"""
RabbitMQ message consumer for user events.

This module implements an event-driven consumer that processes user lifecycle
events from RabbitMQ. It demonstrates the consumer side of the event-driven
architecture and maintains trace_id correlation for end-to-end observability.

The consumer logs all received events with their trace_id for monitoring
and debugging purposes.
"""

import asyncio
import json
from typing import Any, Dict

import aio_pika
import structlog
from aio_pika.abc import AbstractIncomingMessage

from app.config import get_settings

# Load application settings
settings = get_settings()

# Get configured logger instance
logger = structlog.get_logger()

# Global variables for consumer lifecycle management
_connection: aio_pika.Connection | None = None
_channel: aio_pika.Channel | None = None
_consumer_task: asyncio.Task | None = None


async def get_connection() -> aio_pika.Connection:
    """
    Get or create a RabbitMQ connection with automatic reconnection.

    Maintains a singleton connection for the consumer that automatically
    reconnects if the connection is lost.

    Returns:
        aio_pika.Connection: Active RabbitMQ connection
    """
    global _connection
    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    return _connection


async def get_channel() -> aio_pika.Channel:
    """
    Get or create a RabbitMQ channel for message consumption.

    Channels provide a lightweight abstraction over connections and can
    be reused for multiple operations.

    Returns:
        aio_pika.Channel: Active RabbitMQ channel
    """
    global _channel
    connection = await get_connection()
    if _channel is None or _channel.is_closed:
        _channel = await connection.channel()
    return _channel


async def user_event_handler(message: AbstractIncomingMessage) -> None:
    """
    Process incoming user event messages from RabbitMQ.

    This handler processes user lifecycle events and logs them with trace_id
    correlation. It demonstrates how events can trigger downstream processing
    while maintaining request traceability.

    The handler supports three event types:
    - user.created: New user registration
    - user.updated: User profile modification
    - user.deleted: User account removal

    Args:
        message: Incoming RabbitMQ message with event data

    Note:
        The handler uses manual acknowledgment (no_ack=False) to ensure
        messages are not lost if processing fails. In production, implement
        proper error handling and dead letter queues.
    """
    async with message.process():  # Automatically acknowledges on success
        try:
            # Parse JSON message payload
            message_data = json.loads(message.body.decode())
            event_type = message_data.get("event_type")
            data = message_data.get("data", {})

            # Extract trace_id for correlation (use message ID as fallback)
            trace_id = message_data.get("trace_id", str(message.message_id or "unknown"))

            # Set trace_id in logging context for this message
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(trace_id=trace_id)

            # Process event based on type
            if event_type == "user.created":
                user_id = data.get("user_id")
                logger.info(f"Received event user.created with user_id={user_id}")
                # TODO: Implement downstream processing (email notifications, etc.)

            elif event_type == "user.updated":
                user_id = data.get("user_id")
                logger.info(f"Received event user.updated with user_id={user_id}")
                # TODO: Implement downstream processing (cache invalidation, etc.)

            elif event_type == "user.deleted":
                user_id = data.get("user_id")
                logger.info(f"Received event user.deleted with user_id={user_id}")
                # TODO: Implement downstream processing (data cleanup, audit logs, etc.)

            else:
                # Log unknown event types for monitoring
                logger.info(f"Received unknown event type: {event_type}", extra=data)

        except Exception as e:
            # Log processing errors with full context
            logger.error(f"Error processing message: {e}", exc_info=True)
            # Message will not be acknowledged, allowing retry or dead lettering


async def start_consumer() -> None:
    """
    Initialize and start the RabbitMQ consumer.

    This function sets up the message queue infrastructure and begins
    consuming user events. It should be called during application startup.

    The consumer:
    - Declares the topic exchange for user events
    - Creates a durable queue for message persistence
    - Binds the queue to all user event routing keys
    - Starts the consumer task for message processing

    Raises:
        Exception: If consumer initialization fails
    """
    global _consumer_task

    try:
        # Get active channel for consumer setup
        channel = await get_channel()

        # Declare topic exchange for user events
        exchange = await channel.declare_exchange(
            "user_events",
            aio_pika.ExchangeType.TOPIC,
            durable=True  # Survives broker restarts
        )

        # Declare durable queue for message persistence
        queue = await channel.declare_queue("user_events_queue", durable=True)

        # Bind queue to exchange with all user event routing keys
        await queue.bind(exchange, "user.created")
        await queue.bind(exchange, "user.updated")
        await queue.bind(exchange, "user.deleted")

        # Start consuming messages asynchronously
        _consumer_task = asyncio.create_task(
            queue.consume(user_event_handler, no_ack=False)
        )

        logger.info("RabbitMQ consumer started")

    except Exception as e:
        logger.error(f"Failed to start RabbitMQ consumer: {e}")
        raise


async def stop_consumer() -> None:
    """
    Gracefully stop the RabbitMQ consumer and clean up resources.

    This function should be called during application shutdown to ensure
    proper cleanup of connections, channels, and consumer tasks.

    The shutdown process:
    1. Cancels the consumer task
    2. Closes the channel
    3. Closes the connection
    """
    global _consumer_task, _channel, _connection

    # Stop the consumer task
    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None

    # Close channel
    if _channel and not _channel.is_closed:
        await _channel.close()
        _channel = None

    # Close connection
    if _connection and not _connection.is_closed:
        await _connection.close()
        _connection = None

    logger.info("RabbitMQ consumer stopped")
