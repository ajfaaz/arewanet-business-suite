import logging
from invoices.models import ActivityLog

logger = logging.getLogger("arewanet_invoice")


def log_activity(user, action, ip_address=None):
    """
    Records domain activity into system ActivityLog database model and standard Python logging.
    """
    logger.info(f"[ActivityLog] User: {user} | Action: {action}")
    try:
        ActivityLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=action
        )
    except Exception as e:
        logger.error(f"Failed to record ActivityLog entry: {e}")


def log_event(event_type, message, level="info"):
    """
    Standard logger wrapper for system events.
    """
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(f"[{event_type.upper()}] {message}")
