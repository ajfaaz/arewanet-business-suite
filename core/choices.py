from django.db import models

class InvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    UNPAID = "UNPAID", "Unpaid"
    PARTIAL = "PARTIAL", "Partially Paid"
    PAID = "PAID", "Paid"
    OVERDUE = "OVERDUE", "Overdue"
    CANCELLED = "CANCELLED", "Cancelled"


class PaymentMethod(models.TextChoices):
    BANK = "BANK", "Bank Transfer"
    CASH = "CASH", "Cash"
    POS = "POS", "POS"
    CHEQUE = "CHEQUE", "Cheque"
    PAYSTACK = "PAYSTACK", "Paystack"
    FLUTTERWAVE = "FLUTTERWAVE", "Flutterwave"


class ProductType(models.TextChoices):
    GOODS = "GOODS", "Physical Goods"
    SERVICE = "SERVICE", "Service"
