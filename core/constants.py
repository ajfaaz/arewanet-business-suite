# Core System Constants
DEFAULT_CURRENCY = "NGN"
DEFAULT_COUNTRY = "Nigeria"
VAT_RATE = 7.5
COMPANY_NAME = "ArewaNet Business Suite"
DATE_FORMAT = "%d/%m/%Y"
INVOICE_PREFIX = "INV"
QUOTATION_PREFIX = "QTN"
RECEIPT_PREFIX = "RCP"


class InvoiceStatus:
    DRAFT = "DRAFT"
    SENT = "SENT"
    UNPAID = "UNPAID"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class QuotationStatus:
    DRAFT = "DRAFT"
    SENT = "SENT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CONVERTED = "CONVERTED"


class PaymentStatus:
    COMPLETED = "COMPLETED"
    PENDING = "PENDING"
    REVERSED = "REVERSED"


class PaymentMethod:
    CASH = "CASH"
    BANK = "BANK"
    CARD = "CARD"
    ONLINE = "ONLINE"
    TRANSFER = "TRANSFER"


class SubscriptionStatus:
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
