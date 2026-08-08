from django.db import models
from invoices.models import Organization, Product
from inventory.constants import MOVEMENT_TYPE_CHOICES, MOVEMENT_TYPE_OPENING


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
                fields=["product", "warehouse", "location"],
                name="unique_product_warehouse_location"
            )
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
