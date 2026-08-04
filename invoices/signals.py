from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Payment, Receipt


@receiver(post_save, sender=Payment)
def create_receipt_and_update_status(sender, instance, created, **kwargs):
    if created:
        Receipt.objects.get_or_create(
            organization=instance.organization,
            payment=instance
        )
    if instance.invoice:
        instance.invoice.update_status()


@receiver(post_delete, sender=Payment)
def update_status_on_delete(sender, instance, **kwargs):
    if instance.invoice_id:
        try:
            instance.invoice.update_status()
        except Exception:
            pass
