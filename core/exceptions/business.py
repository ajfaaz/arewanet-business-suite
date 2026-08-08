from rest_framework.exceptions import APIException


class BusinessRuleError(APIException):
    status_code = 400
    default_detail = "A business rule was violated."
    default_code = "business_rule_error"


class InvoiceAlreadyPaid(BusinessRuleError):
    default_detail = "This invoice has already been fully paid."
    default_code = "invoice_already_paid"


class PaymentExceedsBalance(BusinessRuleError):
    default_detail = "Payment amount exceeds the outstanding balance."
    default_code = "payment_exceeds_balance"


class InvalidQuotationStatus(BusinessRuleError):
    default_detail = "This quotation cannot be converted in its current status."
    default_code = "invalid_quotation_status"
