from django.db import models
from django.conf import settings


class ActivityLog(models.Model):

    ACTIONS = [
        ("CREATE", "Created"),
        ("UPDATE", "Updated"),
        ("EMAIL", "Emailed"),
        ("PRINT", "Printed"),
        ("PAYMENT", "Payment Received"),
        ("DELETE", "Deleted"),
    ]

    document_type = models.CharField(max_length=50)

    document_id = models.PositiveIntegerField()

    action = models.CharField(max_length=20, choices=ACTIONS)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_activity_logs"
    )

    timestamp = models.DateTimeField(auto_now_add=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.document_type} - {self.action}"
