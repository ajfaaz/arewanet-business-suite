class CoreAppException(Exception):
    """Base exception for ABS platform domain errors."""
    pass

class InvoiceException(CoreAppException):
    pass

class PaymentException(CoreAppException):
    pass

class CustomerException(CoreAppException):
    pass

class ProductException(CoreAppException):
    pass
