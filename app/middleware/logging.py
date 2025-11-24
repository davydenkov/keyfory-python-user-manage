"""
Logging middleware with comprehensive request tracing and trace_id support.

This middleware implements the mandatory logging requirements by:
- Generating or extracting trace_id from request headers
- Adding trace_id to all log entries for request correlation
- Logging request start, completion, and errors with timing
- Returning trace_id in response headers for client tracking

The middleware uses structlog for structured JSON logging with context variables.
"""

import time
import uuid
from typing import Any, Dict, override

import structlog
from litestar import Request, Response
from litestar.middleware.base import MiddlewareProtocol
from litestar.types import ASGIApp, Receive, Scope, Send

from app.config import get_settings

# Load application settings
settings = get_settings()

# Configure structlog for structured JSON logging
structlog.configure(
    processors=[
        # Merge context variables (including trace_id) into log records
        structlog.contextvars.merge_contextvars,
        # Add log level to each record
        structlog.processors.add_log_level,
        # Add ISO format timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Render as JSON for easy parsing by log aggregators
        structlog.processors.JSONRenderer(),
    ],
    # Filter logs based on configured log level
    wrapper_class=structlog.make_filtering_bound_logger(settings.log_level),
    # Use dict for context storage
    context_class=dict,
    # Use standard write logger factory
    logger_factory=structlog.WriteLoggerFactory(),
    # Cache logger instances for performance
    cache_logger_on_first_use=True,
)

# Get configured logger instance
logger = structlog.get_logger()


class LoggingMiddleware(MiddlewareProtocol):
    """
    ASGI middleware for comprehensive request logging with trace_id support.

    This middleware implements the mandatory logging requirements by intercepting
    all HTTP requests to add structured logging with unique trace identifiers.
    It provides end-to-end request tracking across all application components.

    Key Features:
    - Generates or extracts trace_id from X-Request-Id header
    - Adds trace_id to structured log context
    - Logs request start with method and path
    - Logs request completion with status and execution time
    - Logs errors with full stack traces
    - Returns trace_id in X-Trace-Id response header

    The trace_id enables correlation of log entries across:
    - API request/response logs
    - Database operations
    - RabbitMQ message publishing
    - RabbitMQ message consumption
    """

    def __init__(self, app: ASGIApp) -> None:
        """
        Initialize the logging middleware.

        Args:
            app: The ASGI application to wrap
        """
        self.app = app

    @override
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handle ASGI request with comprehensive logging.

        This method intercepts each HTTP request to add logging and tracing.
        Non-HTTP requests (like lifespan events) are passed through unchanged.

        Args:
            scope: ASGI scope dictionary containing request information
            receive: ASGI receive callable
            send: ASGI send callable
        """
        # Only process HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate or extract trace_id from request headers
        headers = dict(scope.get("headers", []))
        trace_id = self._get_trace_id_from_headers(headers)

        # Set trace_id in structlog context for all subsequent logging
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        # Extract request information for logging
        method = scope.get("method", "")
        path = scope.get("path", "")
        query_string = scope.get("query_string", b"").decode()

        # Build full request path including query parameters
        full_path = path
        if query_string:
            full_path += f"?{query_string}"

        # Log request initiation
        logger.info(
            "Request started",
            method=method,
            path=full_path,
        )

        # Record start time for performance monitoring
        start_time = time.time()

        # Initialize response tracking variables
        response_status = None
        response_headers = []

        async def logging_send(message: Dict[str, Any]) -> None:
            """
            Custom send function to intercept and modify response.

            This function captures response information and adds the trace_id
            to response headers for client-side tracking.

            Args:
                message: ASGI message dictionary
            """
            nonlocal response_status, response_headers

            if message["type"] == "http.response.start":
                # Capture response status and headers
                response_status = message["status"]
                response_headers = message.get("headers", [])

                # Add trace_id to response headers for client tracking
                trace_id_bytes = trace_id.encode()
                message["headers"] = message.get("headers", []) + [
                    [b"X-Trace-Id", trace_id_bytes]
                ]

            # Send the (possibly modified) message
            await send(message)

        try:
            # Process the request through the application
            await self.app(scope, receive, logging_send)

            # Calculate total request execution time
            execution_time = time.time() - start_time

            # Log successful request completion
            logger.info(
                "Request completed",
                method=method,
                path=full_path,
                status=response_status,
                execution_time=f"{execution_time:.4f}s",
                performance=f"{'fast' if execution_time < 0.1 else 'normal' if execution_time < 1.0 else 'slow'}",
            )

        except Exception as exc:
            # Calculate execution time for failed requests
            execution_time = time.time() - start_time

            # Log request failure with error details
            logger.error(
                "Request failed",
                method=method,
                path=full_path,
                execution_time=f"{execution_time:.4f}s",
                error=str(exc),
                exc_info=True,  # Include full stack trace
            )
            # Re-raise the exception to maintain error handling flow
            raise

    def _get_trace_id_from_headers(self, headers: Dict[bytes, bytes]) -> str:
        """
        Extract or generate trace_id from request headers.

        Checks for X-Request-Id header first. If present, uses its value.
        Otherwise, generates a new UUID4 as the trace_id.

        Args:
            headers: Dictionary of request headers (bytes to bytes)

        Returns:
            str: The trace_id for this request
        """
        # Check for X-Request-Id header (standard tracing header)
        request_id_header = headers.get(b"x-request-id")
        if request_id_header:
            try:
                # Decode bytes to string
                return request_id_header.decode()
            except UnicodeDecodeError:
                # If decoding fails, fall through to generate new ID
                pass

        # Generate new UUID4 trace_id if none provided or invalid
        return str(uuid.uuid4())
