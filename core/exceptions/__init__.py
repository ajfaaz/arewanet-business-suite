from .business import (
    BusinessRuleError,
    InvoiceAlreadyPaid,
    PaymentExceedsBalance,
    InvalidQuotationStatus,
)
from .inventory import (
    InsufficientStockError,
    InsufficientStock,
    WarehouseOrganizationMismatch,
    InvalidDocumentStatusError,
)


class CoreAppException(Exception):
    """Base exception for ABS platform domain errors."""
    default_message = "A domain exception occurred."

    def __init__(self, message=None):
        self.message = message or self.default_message
        super().__init__(self.message)


class CustomerException(CoreAppException):
    pass


class CustomerNotFound(CustomerException):
    default_message = "Customer requested does not exist."


class InvoiceException(CoreAppException):
    pass


class InvoiceNotFound(InvoiceException):
    default_message = "Invoice requested does not exist."


class InvalidInvoiceStatusException(InvoiceException):
    default_message = "Operation invalid for current invoice status."


class PaymentException(CoreAppException):
    pass


class PaymentNotFound(PaymentException):
    default_message = "Payment requested does not exist."


class InvalidPaymentException(PaymentException):
    default_message = "Invalid payment transaction parameters."


class InsufficientBalanceException(PaymentException):
    default_message = "Payment amount exceeds outstanding invoice balance."


class QuotationException(CoreAppException):
    pass


class QuotationNotFound(QuotationException):
    default_message = "Quotation requested does not exist."


class ProductException(CoreAppException):
    pass


class ProductNotFound(ProductException):
    default_message = "Product requested does not exist."


class SubscriptionException(CoreAppException):
    pass


class SubscriptionNotFound(SubscriptionException):
    default_message = "Subscription requested does not exist."


__all__ = [
    "BusinessRuleError",
    "InvoiceAlreadyPaid",
    "PaymentExceedsBalance",
    "InvalidQuotationStatus",
    "InsufficientStockError",
    "WarehouseOrganizationMismatch",
    "CoreAppException",
    "CustomerException",
    "CustomerNotFound",
    "InvoiceException",
    "InvoiceNotFound",
    "InvalidInvoiceStatusException",
    "PaymentException",
    "PaymentNotFound",
    "InvalidPaymentException",
    "InsufficientBalanceException",
    "QuotationException",
    "QuotationNotFound",
    "ProductException",
    "ProductNotFound",
    "SubscriptionException",
    "SubscriptionNotFound",
]
