import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.notification import Notification

logger = logging.getLogger(__name__)


def create_notification(
    db: Session,
    user_id: uuid.UUID,
    notification_type: str,
    title: str,
    body: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Notification:
    """
    Persist a notification record for a user.
    Returns the created Notification ORM instance.
    """
    notification = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        type=notification_type,
        title=title,
        body=body or "",
        metadata=metadata or {},
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    logger.info(
        "Notification created: type=%s user=%s", notification_type, user_id
    )
    return notification


def mark_read(db: Session, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Mark a single notification as read. Returns True if found and updated."""
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        .first()
    )
    if not notification:
        return False
    notification.is_read = True
    db.commit()
    return True


def get_unread_count(db: Session, user_id: uuid.UUID) -> int:
    """Return the count of unread notifications for a user."""
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read == False)
        .count()
    )
