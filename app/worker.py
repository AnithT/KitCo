"""
Celery worker — handles background tasks like broadcast message sending.

Run with:
    celery -A app.worker.celery_app worker --loglevel=info
"""

import logging
from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "kitco",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # fair dispatch for broadcast fan-out
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_broadcast_messages(self, broadcast_id: str):
    """
    Fan out messages for a broadcast.
    Reads recipient records from DB, sends each via Twilio, updates status.

    Uses sync DB + Twilio calls since Celery workers are sync by default.
    """
    import uuid
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.models.broadcast import Broadcast, BroadcastRecipient, RecipientStatus
    from app.services.messaging_service import send_message

    # Sync engine for Celery (asyncpg → psycopg2)
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(sync_url)

    with Session(engine) as db:
        broadcast = db.execute(
            select(Broadcast).where(Broadcast.id == uuid.UUID(broadcast_id))
        ).scalar_one_or_none()

        if not broadcast:
            logger.error("Broadcast %s not found", broadcast_id)
            return

        recipients = db.execute(
            select(BroadcastRecipient).where(
                BroadcastRecipient.broadcast_id == broadcast.id,
                BroadcastRecipient.status == RecipientStatus.QUEUED,
            )
        ).scalars().all()

        logger.info(
            "Sending broadcast %s to %d recipients", broadcast_id, len(recipients)
        )

        for recipient in recipients:
            try:
                message_sid = send_message(
                    to_phone=recipient.phone,
                    body=broadcast.message_template,
                    channel=broadcast.channel,
                )
                recipient.twilio_message_sid = message_sid
                recipient.status = RecipientStatus.SENT
            except Exception as exc:
                logger.error(
                    "Failed to send to %s: %s", recipient.phone, exc
                )
                recipient.status = RecipientStatus.FAILED

            db.commit()

        logger.info("Broadcast %s complete", broadcast_id)
