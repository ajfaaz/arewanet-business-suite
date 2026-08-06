from django.db import models

class InvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    UNPAID = "UNPAID", "Unpaid"
    PARTIAL = "PARTIAL", "Partially Paid"
    PAID = "PAID", "Paid"
    OVERDUE = "OVERDUE", "Overdue"
    CANCELLED = "CANCELLED", "Cancelled"


class QuotationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SENT = "SENT", "Sent"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    EXPIRED = "EXPIRED", "Expired"
    CONVERTED = "CONVERTED", "Converted"


class PaymentMethod(models.TextChoices):
    CASH = "CASH", "Cash"
    BANK = "BANK", "Bank Transfer"
    POS = "POS", "POS"
    CHEQUE = "CHEQUE", "Cheque"
    ONLINE = "ONLINE", "Online Payment"
    MOBILE = "MOBILE", "Mobile Money"
    PAYSTACK = "PAYSTACK", "Paystack"
    FLUTTERWAVE = "FLUTTERWAVE", "Flutterwave"


class PaymentStatus(models.TextChoices):
    COMPLETED = "COMPLETED", "Completed"
    PENDING = "PENDING", "Pending"
    FAILED = "FAILED", "Failed"
    REVERSED = "REVERSED", "Reversed"
    REFUNDED = "REFUNDED", "Refunded"


class ProductType(models.TextChoices):
    GOODS = "GOODS", "Physical Goods"
    SERVICE = "SERVICE", "Service"


class CreditNoteStatus(models.TextChoices):
    ISSUED = "ISSUED", "Issued"
    APPLIED = "APPLIED", "Applied"
    CANCELLED = "CANCELLED", "Cancelled"


class DebitNoteStatus(models.TextChoices):
    ISSUED = "ISSUED", "Issued"
    CANCELLED = "CANCELLED", "Cancelled"


class BillingCycle(models.TextChoices):
    WEEKLY = "WEEKLY", "Weekly"
    MONTHLY = "MONTHLY", "Monthly"
    QUARTERLY = "QUARTERLY", "Quarterly"
    SEMI_ANNUAL = "SEMI_ANNUAL", "Semi Annual"
    ANNUAL = "ANNUAL", "Annual"


class SubscriptionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    PAUSED = "PAUSED", "Paused"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


class DocumentType(models.TextChoices):
    QUOTATION = "QUOTATION", "Quotation"
    INVOICE = "INVOICE", "Invoice"
    RECEIPT = "RECEIPT", "Receipt"
    CREDIT_NOTE = "CREDIT_NOTE", "Credit Note"
    DEBIT_NOTE = "DEBIT_NOTE", "Debit Note"
    STATEMENT = "STATEMENT", "Customer Statement"
    SUBSCRIPTION = "SUBSCRIPTION", "Subscription"

