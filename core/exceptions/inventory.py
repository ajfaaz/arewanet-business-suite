from core.exceptions.business import BusinessRuleError


class InsufficientStockError(BusinessRuleError):
    """
    Raised when attempting to issue more stock than available in a warehouse/location.
    """
    code = "insufficient_stock"
    default_code = "insufficient_stock"
    message = "There is not enough stock available."
    default_detail = "There is not enough stock available."


InsufficientStock = InsufficientStockError


class WarehouseOrganizationMismatch(BusinessRuleError):
    """
    Raised when operations involve warehouses or products from different organizations.
    """
    code = "WAREHOUSE_ORGANIZATION_MISMATCH"
    message = "Warehouse and product must belong to the same organization."
