from sales.models import ActivityLog


def log_activity(user, document, action, notes=""):
    """
    Automatically log activity for any sales document.

    Example:
    log_activity(user=request.user, document=invoice, action="PRINT", notes="Printed standard template")
    """
    user_obj = user if user and getattr(user, 'is_authenticated', False) else None

    return ActivityLog.objects.create(
        user=user_obj,
        document_type=document.__class__.__name__,
        document_id=document.pk,
        action=action,
        notes=notes
    )
