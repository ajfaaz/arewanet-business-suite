from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from invoices.models import Organization, Product
from inventory.constants import (
    MOVEMENT_TYPE_CHOICES,
    MOVEMENT_TYPE_OPENING,
    DOC_STATUS_DRAFT,
    DOC_STATUS_CHOICES,
)

User = get_user_model()


class Warehouse(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="warehouses"
    )
    name = models.CharField(
        max_length=255
    )
    code = models.CharField(
        max_length=50
    )
    address = models.TextField(
        blank=True
    )
    is_active = models.BooleanField(
        default=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_warehouse_code_per_organization"
            )
        ]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class WarehouseLocation(models.Model):
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="locations"
    )
    name = models.CharField(
        max_length=255
    )
    code = models.CharField(
        max_length=50
    )
    is_active = models.BooleanField(
        default=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["warehouse", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "code"],
                name="unique_location_code_per_warehouse"
            )
        ]
        indexes = [
            models.Index(fields=["warehouse", "is_active"]),
        ]

    def __str__(self):
        return f"{self.warehouse.code} - {self.name} ({self.code})"


class InventoryItem(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="inventory_items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="inventory_items"
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="inventory_items"
    )
    location = models.ForeignKey(
        WarehouseLocation,
        on_delete=models.CASCADE,
        related_name="inventory_items",
        null=True,
        blank=True
    )
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["product", "warehouse"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "warehouse"],
                condition=models.Q(location__isnull=True),
                name="unique_product_warehouse_without_location",
            ),
            models.UniqueConstraint(
                fields=["product", "warehouse", "location"],
                condition=models.Q(location__isnull=False),
                name="unique_product_warehouse_location",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "product"]),
            models.Index(fields=["warehouse", "product"]),
        ]

    def __str__(self):
        loc_str = f" / {self.location.code}" if self.location else ""
        return f"{self.product.name} @ {self.warehouse.code}{loc_str}: {self.quantity}"


class StockMovement(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="stock_movements"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="stock_movements"
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="stock_movements"
    )
    location = models.ForeignKey(
        WarehouseLocation,
        on_delete=models.PROTECT,
        related_name="stock_movements",
        null=True,
        blank=True
    )
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )
    movement_type = models.CharField(
        max_length=30,
        choices=MOVEMENT_TYPE_CHOICES,
        default=MOVEMENT_TYPE_OPENING
    )
    reference_type = models.CharField(
        max_length=50,
        blank=True
    )
    reference_id = models.PositiveBigIntegerField(
        null=True,
        blank=True
    )
    notes = models.TextField(
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "product"]),
            models.Index(fields=["warehouse", "product"]),
            models.Index(fields=["movement_type", "created_at"]),
        ]

    def __str__(self):
        sign = "+" if self.quantity > 0 else ""
        return f"[{self.movement_type}] {self.product.name} ({sign}{self.quantity}) @ {self.warehouse.code}"


class BaseInventoryDocument(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE
    )
    document_number = models.CharField(
        max_length=50
    )
    status = models.CharField(
        max_length=20,
        choices=DOC_STATUS_CHOICES,
        default=DOC_STATUS_DRAFT
    )
    notes = models.TextField(
        blank=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True
    )
    completed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        abstract = True


class GoodsReceivedNote(BaseInventoryDocument):
    purchase_order = models.ForeignKey(
        'purchases.PurchaseOrder',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="grns"
    )
    supplier_name = models.CharField(
        max_length=255,
        blank=True
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="goods_received_notes"
    )
    received_date = models.DateField()

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "document_number"],
                name="unique_grn_number_per_org"
            )
        ]

    def __str__(self):
        return f"{self.document_number} ({self.status}) @ {self.warehouse.code}"


class GoodsReceivedNoteItem(models.Model):
    grn = models.ForeignKey(
        GoodsReceivedNote,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )
    unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.grn.document_number}: {self.product.name} x {self.quantity}"


class GoodsIssueNote(BaseInventoryDocument):
    invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="goods_issue_notes",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="goods_issue_notes"
    )
    issue_date = models.DateField()

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "document_number"],
                name="unique_gin_number_per_org"
            )
        ]

    def __str__(self):
        return f"{self.document_number} ({self.status}) @ {self.warehouse.code}"


class GoodsIssueNoteItem(models.Model):
    gin = models.ForeignKey(
        GoodsIssueNote,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.gin.document_number}: {self.product.name} x {self.quantity}"


class StockTransferDocument(BaseInventoryDocument):
    source_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="outgoing_transfers"
    )
    destination_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="incoming_transfers"
    )
    transfer_date = models.DateField()

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "document_number"],
                name="unique_transfer_number_per_org"
            )
        ]

    def __str__(self):
        return f"{self.document_number} ({self.status}) {self.source_warehouse.code} -> {self.destination_warehouse.code}"


class StockTransferDocumentItem(models.Model):
    transfer = models.ForeignKey(
        StockTransferDocument,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.transfer.document_number}: {self.product.name} x {self.quantity}"


class StockAdjustmentDocument(BaseInventoryDocument):
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="adjustments"
    )
    adjustment_date = models.DateField()

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "document_number"],
                name="unique_adjustment_number_per_org"
            )
        ]

    def __str__(self):
        return f"{self.document_number} ({self.status}) @ {self.warehouse.code}"


class StockAdjustmentDocumentItem(models.Model):
    adjustment = models.ForeignKey(
        StockAdjustmentDocument,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )
    system_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )
    counted_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )
    difference = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )
    reason = models.TextField(
        blank=True
    )

    def __str__(self):
        return f"{self.adjustment.document_number}: {self.product.name} (Diff: {self.difference})"


class StockAlert(models.Model):
    ALERT_TYPES = (
        ("OUT_OF_STOCK", "Out of Stock"),
        ("LOW_STOCK", "Low Stock"),
        ("OVERSTOCK", "Overstock"),
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="stock_alerts"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stock_alerts"
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="stock_alerts"
    )

    alert_type = models.CharField(
        max_length=30,
        choices=ALERT_TYPES
    )

    current_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )

    threshold = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00")
    )

    is_resolved = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        wh_code = self.warehouse.code if self.warehouse else "Global"
        return f"[{self.alert_type}] {self.product.name} @ {wh_code} (Qty: {self.current_quantity}, Resolved: {self.is_resolved})"


class PurchaseReturnDocument(BaseInventoryDocument):
    purchase_order = models.ForeignKey(
        "purchases.PurchaseOrder",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="purchase_returns",
    )

    supplier = models.ForeignKey(
        "purchases.Supplier",
        on_delete=models.PROTECT,
        related_name="purchase_returns",
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="purchase_returns",
    )

    return_date = models.DateField()

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "document_number"],
                name="unique_purchase_return_number_per_org",
            )
        ]

    def __str__(self):
        return (
            f"{self.document_number} "
            f"({self.status}) @ {self.warehouse.code}"
        )


class PurchaseReturnDocumentItem(models.Model):
    purchase_return = models.ForeignKey(
        PurchaseReturnDocument,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
    )

    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )

    reason = models.TextField(blank=True)

    def __str__(self):
        return (
            f"{self.purchase_return.document_number}: "
            f"{self.product.name} x {self.quantity}"
        )

