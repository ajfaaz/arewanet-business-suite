from invoices.models import ActivityLog

class AuditService:
    @staticmethod
    def log(user, action, reference=None):
        """
        Record an audit activity log entry.
        """
        if user and user.is_authenticated:
            return ActivityLog.objects.create(
                user=user,
                action=action
            )
        return None
