from django.core.mail import send_mail
from django.conf import settings

class NotificationService:

    @staticmethod
    def send_invoice_email(invoice):
        """
        Send invoice notification email to the customer.
        """
        if not invoice.customer.email:
            return False

        subject = f"Invoice {invoice.invoice_no} from {invoice.organization.name}"
        message = f"Dear {invoice.customer.company_name},\n\nPlease find your invoice {invoice.invoice_no} for total amount ₦{invoice.total_due:.2f}.\nDue Date: {invoice.due_date}\n\nThank you for your business!"

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@arewanet.com'),
                recipient_list=[invoice.customer.email],
                fail_silently=True
            )
            return True
        except Exception:
            return False

    @staticmethod
    def send_payment_receipt(payment):
        """
        Send payment confirmation receipt email.
        """
        if not payment.invoice.customer.email:
            return False

        subject = f"Payment Receipt for Invoice {payment.invoice.invoice_no}"
        message = f"Dear {payment.invoice.customer.company_name},\n\nWe have received your payment of ₦{payment.amount:.2f} via {payment.payment_method}.\nReceipt No: {payment.receipt_no}\n\nThank you!"

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@arewanet.com'),
                recipient_list=[payment.invoice.customer.email],
                fail_silently=True
            )
            return True
        except Exception:
            return False

    @staticmethod
    def send_overdue_reminder(invoice):
        """
        Send automated reminder email for overdue invoices.
        """
        if not invoice.customer.email:
            return False

        subject = f"OVERDUE REMINDER: Invoice {invoice.invoice_no}"
        message = f"Dear {invoice.customer.company_name},\n\nThis is a reminder that invoice {invoice.invoice_no} was due on {invoice.due_date}.\nOutstanding Balance: ₦{invoice.balance:.2f}.\n\nPlease arrange payment at your earliest convenience."

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@arewanet.com'),
                recipient_list=[invoice.customer.email],
                fail_silently=True
            )
            return True
        except Exception:
            return False
