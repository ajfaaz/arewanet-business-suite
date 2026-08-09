from decimal import Decimal
from django.db.models import Sum, Q, F
from django.utils import timezone
from datetime import datetime, timedelta

from invoices.models import Organization, Product
from inventory.models import Warehouse, InventoryItem, StockMovement, StockAlert


class StockLevelService:

    @staticmethod
    def get_status(product, warehouse=None, current_quantity=None):
        """
        Calculate stock status for a given product (OUT_OF_STOCK, LOW_STOCK, OVERSTOCK, NORMAL).
        """
        if current_quantity is not None:
            qty = Decimal(str(current_quantity))
        elif warehouse:
            item = InventoryItem.objects.filter(product=product, warehouse=warehouse).first()
            qty = Decimal(str(item.quantity)) if item else Decimal("0.00")
        else:
            total_qty = InventoryItem.objects.filter(product=product).aggregate(total=Sum("quantity"))["total"]
            qty = Decimal(str(total_qty or 0))

        if qty <= 0:
            return "OUT_OF_STOCK"

        reorder = Decimal(str(product.reorder_level or 0))
        if reorder > 0 and qty <= reorder:
            return "LOW_STOCK"

        if product.maximum_stock is not None:
            max_stock = Decimal(str(product.maximum_stock))
            if max_stock > 0 and qty > max_stock:
                return "OVERSTOCK"

        return "NORMAL"


class StockAlertService:

    @staticmethod
    def evaluate(product, warehouse=None):
        """
        Evaluates stock thresholds for product/warehouse and updates/resolves StockAlert entries.
        """
        if not product or not getattr(product, 'is_stockable', True):
            return

        org = product.organization
        status_name = StockLevelService.get_status(product, warehouse=warehouse)

        if warehouse:
            item = InventoryItem.objects.filter(organization=org, product=product, warehouse=warehouse).first()
            current_qty = Decimal(str(item.quantity)) if item else Decimal("0.00")
        else:
            total_qty = InventoryItem.objects.filter(organization=org, product=product).aggregate(total=Sum("quantity"))["total"]
            current_qty = Decimal(str(total_qty or 0))

        if status_name in ("OUT_OF_STOCK", "LOW_STOCK", "OVERSTOCK"):
            threshold = Decimal(str(product.reorder_level or 0)) if status_name in ("OUT_OF_STOCK", "LOW_STOCK") else Decimal(str(product.maximum_stock or 0))

            alert = StockAlert.objects.filter(
                organization=org,
                product=product,
                warehouse=warehouse,
                is_resolved=False
            ).first()

            if alert:
                alert.alert_type = status_name
                alert.current_quantity = current_qty
                alert.threshold = threshold
                alert.save(update_fields=["alert_type", "current_quantity", "threshold"])
            else:
                StockAlert.objects.create(
                    organization=org,
                    product=product,
                    warehouse=warehouse,
                    alert_type=status_name,
                    current_quantity=current_qty,
                    threshold=threshold,
                    is_resolved=False
                )
        else:
            active_alerts = StockAlert.objects.filter(
                organization=org,
                product=product,
                warehouse=warehouse,
                is_resolved=False
            )
            for alert in active_alerts:
                alert.is_resolved = True
                alert.current_quantity = current_qty
                alert.resolved_at = timezone.now()
                alert.save(update_fields=["is_resolved", "current_quantity", "resolved_at"])


class InventoryValuationService:

    @staticmethod
    def get_value(organization, warehouse=None):
        """
        Calculates total inventory valuation based on current quantity and product cost price.
        """
        items = InventoryItem.objects.filter(organization=organization).select_related("product")
        if warehouse:
            items = items.filter(warehouse=warehouse)

        total_value = Decimal("0.00")
        for item in items:
            if item.quantity > 0 and item.product:
                cost = item.product.cost_price if item.product.cost_price > 0 else item.product.selling_price
                total_value += (Decimal(str(item.quantity)) * Decimal(str(cost)))
        return total_value


class InventoryAnalyticsSelector:

    @staticmethod
    def get_dashboard_summary(organization, warehouse=None):
        products = Product.objects.filter(organization=organization, active=True, is_stockable=True)
        total_products = products.count()

        out_of_stock_count = 0
        low_stock_count = 0

        for p in products:
            st = StockLevelService.get_status(p, warehouse=warehouse)
            if st == "OUT_OF_STOCK":
                out_of_stock_count += 1
            elif st == "LOW_STOCK":
                low_stock_count += 1

        items = InventoryItem.objects.filter(organization=organization)
        if warehouse:
            items = items.filter(warehouse=warehouse)
        total_units = items.aggregate(total=Sum("quantity"))["total"] or Decimal("0.00")

        inventory_value = InventoryValuationService.get_value(organization, warehouse=warehouse)

        today = timezone.now().date()
        movements_today = StockMovement.objects.filter(organization=organization, created_at__date=today)
        if warehouse:
            movements_today = movements_today.filter(warehouse=warehouse)

        stock_in_today = movements_today.filter(quantity__gt=0).aggregate(total=Sum("quantity"))["total"] or Decimal("0.00")
        stock_out_today = movements_today.filter(quantity__lt=0).aggregate(total=Sum("quantity"))["total"] or Decimal("0.00")

        return {
            "products": {
                "total": total_products,
                "out_of_stock": out_of_stock_count,
                "low_stock": low_stock_count,
            },
            "stock": {
                "total_units": f"{Decimal(str(total_units)):.2f}",
                "inventory_value": f"{Decimal(str(inventory_value)):.2f}",
            },
            "movements": {
                "stock_in_today": f"{Decimal(str(stock_in_today)):.2f}",
                "stock_out_today": f"{Decimal(str(abs(stock_out_today))):.2f}",
            }
        }

    @staticmethod
    def get_statistics(organization, from_date=None, to_date=None, warehouse=None):
        qs = StockMovement.objects.filter(organization=organization)
        if warehouse:
            qs = qs.filter(warehouse=warehouse)
        if from_date:
            qs = qs.filter(created_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(created_at__date__lte=to_date)

        stock_in = qs.filter(quantity__gt=0).aggregate(total=Sum("quantity"))["total"] or Decimal("0.00")
        stock_out = qs.filter(quantity__lt=0).aggregate(total=Sum("quantity"))["total"] or Decimal("0.00")

        adjustments_in = qs.filter(movement_type="ADJUSTMENT_IN").aggregate(total=Sum("quantity"))["total"] or Decimal("0.00")
        adjustments_out = qs.filter(movement_type="ADJUSTMENT_OUT").aggregate(total=Sum("quantity"))["total"] or Decimal("0.00")
        total_adjustments = adjustments_in + adjustments_out

        transfers = qs.filter(movement_type__in=["TRANSFER_IN", "TRANSFER_OUT"]).aggregate(total=Sum("quantity"))["total"] or Decimal("0.00")

        return {
            "period": {
                "from": str(from_date) if from_date else None,
                "to": str(to_date) if to_date else None,
            },
            "stock_in": f"{Decimal(str(stock_in)):.2f}",
            "stock_out": f"{Decimal(str(abs(stock_out))):.2f}",
            "adjustments": f"{Decimal(str(total_adjustments)):.2f}",
            "transfers": f"{Decimal(str(abs(transfers))):.2f}",
        }

    @staticmethod
    def get_recent_movements(organization, warehouse=None, product=None, movement_type=None, limit=20):
        qs = StockMovement.objects.filter(organization=organization).select_related("product", "warehouse")
        if warehouse:
            qs = qs.filter(warehouse=warehouse)
        if product:
            qs = qs.filter(product=product)
        if movement_type:
            qs = qs.filter(movement_type=movement_type)
        return qs.order_by("-created_at")[:limit]

    @staticmethod
    def get_top_products(organization, from_date=None, to_date=None, limit=10):
        qs = StockMovement.objects.filter(organization=organization, quantity__lt=0).select_related("product")
        if from_date:
            qs = qs.filter(created_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(created_at__date__lte=to_date)

        aggregated = (
            qs.values("product_id", "product__name", "product__sku")
            .annotate(total_moved=Sum("quantity"))
            .order_by("total_moved")[:limit]
        )

        results = []
        for row in aggregated:
            results.append({
                "product_id": row["product_id"],
                "product_name": row["product__name"],
                "product_sku": row["product__sku"],
                "units_moved": str(abs(row["total_moved"] or 0)),
            })
        return results

    @staticmethod
    def get_slow_moving_products(organization, days=30, limit=10):
        cutoff = timezone.now() - timedelta(days=days)
        items = InventoryItem.objects.filter(organization=organization, quantity__gt=0).select_related("product", "warehouse")

        results = []
        for item in items:
            last_movement = StockMovement.objects.filter(
                organization=organization,
                product=item.product,
                warehouse=item.warehouse
            ).order_by("-created_at").first()

            if not last_movement or last_movement.created_at < cutoff:
                results.append({
                    "product_id": item.product.id,
                    "product_name": item.product.name,
                    "warehouse_code": item.warehouse.code,
                    "stock": str(item.quantity),
                    "last_movement_date": str(last_movement.created_at.date()) if last_movement else "No Movements",
                })
                if len(results) >= limit:
                    break

        return results

    @staticmethod
    def get_reorder_recommendations(organization, warehouse=None):
        products = Product.objects.filter(organization=organization, active=True, is_stockable=True, reorder_level__gt=0)
        recommendations = []

        for p in products:
            status_name = StockLevelService.get_status(p, warehouse=warehouse)
            if status_name in ("OUT_OF_STOCK", "LOW_STOCK"):
                if warehouse:
                    item = InventoryItem.objects.filter(product=p, warehouse=warehouse).first()
                    current_qty = item.quantity if item else Decimal("0.00")
                else:
                    total_qty = InventoryItem.objects.filter(product=p).aggregate(total=Sum("quantity"))["total"]
                    current_qty = Decimal(str(total_qty or 0))

                max_stock = Decimal(str(p.maximum_stock)) if p.maximum_stock else (Decimal(str(p.reorder_level)) * Decimal("2.00"))
                rec_qty = max(Decimal("0.00"), max_stock - current_qty)

                recommendations.append({
                    "product_id": p.id,
                    "product_name": p.name,
                    "current_stock": str(current_qty),
                    "reorder_level": str(p.reorder_level),
                    "recommended_quantity": str(rec_qty),
                })

        return recommendations
