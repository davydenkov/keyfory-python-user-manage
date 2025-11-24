"""
RabbitMQ message producer for user events.

This module provides functionality to publish user lifecycle events to RabbitMQ.
It supports event-driven architecture by broadcasting user creation, updates,
and deletions to downstream consumers.

The producer includes trace_id in all messages to maintain request correlation
across the entire application stack.
"""

import json
from typing import Any, Dict

import aio_pika
import structlog
from aio_pika import Message

from app.config import get_settings

# Load application settings
settings = get_settings()

# Global connection and channel for connection reuse and performance
_connection: aio_pika.Connection | None = None
_channel: aio_pika.Channel | None = None


async def get_connection() -> aio_pika.Connection:
    """
    Get or create a RabbitMQ connection with automatic reconnection.

    This function maintains a singleton connection that survives across
    multiple publish operations. It automatically reconnects if the
    connection is lost.

    Returns:
        aio_pika.Connection: Active RabbitMQ connection
    """
    global _connection
    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    return _connection


async def get_channel() -> aio_pika.Channel:
    """
    Get or create a RabbitMQ channel for message publishing.

    Channels are lightweight and can be reused for multiple operations.
    This function ensures an active channel is always available.

    Returns:
        aio_pika.Channel: Active RabbitMQ channel
    """
    global _channel
    connection = await get_connection()
    if _channel is None or _channel.is_closed:
        _channel = await connection.channel()
    return _channel


async def publish_user_event(event_type: str, data: Dict[str, Any]) -> None:
    """
    Publish a user event to RabbitMQ for event-driven processing.

    This function broadcasts user lifecycle events (created, updated, deleted)
    to enable decoupled processing by consumer applications. Each message
    includes the trace_id from the current request context for correlation.

    Args:
        event_type: Type of event ("user.created", "user.updated", "user.deleted")
        data: Event-specific data (typically contains user_id)

    Note:
        This function is designed to be fire-and-forget. If publishing fails,
        it logs the error but doesn't raise exceptions to avoid breaking
        the main application flow.

        In production, consider implementing:
        - Message persistence for failed publishes
        - Retry mechanisms with exponential backoff
        - Dead letter queues for unprocessable messages

    Example:
        await publish_user_event("user.created", {"user_id": 123})
    """
    try:
        # Get active channel for publishing
        channel = await get_channel()

        # Declare topic exchange for user events
        # Topic exchanges allow routing based on event types
        exchange = await channel.declare_exchange(
            "user_events",
            aio_pika.ExchangeType.TOPIC,
            durable=True  # Survives broker restarts
        )

        # Extract trace_id from current logging context
        # This maintains request correlation across the entire system
        current_context = structlog.contextvars.get_contextvars()
        trace_id = current_context.get("trace_id", "unknown")

        # Prepare message payload with event metadata
        message_data = {
            "event_type": event_type,
            "data": data,
            "trace_id": trace_id,
        }
        message_body = json.dumps(message_data).encode()

        # Create message with persistence and content type
        message = Message(
            body=message_body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,  # Survive broker restarts
            content_type="application/json",
        )

        # Publish message with routing key matching event type
        await exchange.publish(message, routing_key=event_type)

    except Exception as e:
        # Log error but don't fail the operation
        # In production, implement proper error handling and retry logic
        print(f"Failed to publish event {event_type}: {e}")
        # TODO: Implement message persistence for failed publishes
