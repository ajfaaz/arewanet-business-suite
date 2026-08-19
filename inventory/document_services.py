from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from core.exceptions import BusinessRuleError, InsufficientStockError, InvalidDocumentStatusError, WarehouseOrganizationMismatch
from inventory.models import (
    InventoryItem,
    GoodsReceivedNote, GoodsReceivedNoteItem,
    GoodsIssueNote, GoodsIssueNoteItem,
    StockTransferDocument, StockTransferDocumentItem,
    StockAdjustmentDocument, StockAdjustmentDocumentItem,
)
from inventory.constants import (
    DOC_STATUS_DRAFT,
    DOC_STATUS_PENDING,
    DOC_STATUS_APPROVED,
    DOC_STATUS_COMPLETED,
    DOC_STATUS_CANCELLED,
    MOVEMENT_TYPE_PURCHASE,
    MOVEMENT_TYPE_SALE,
)
from inventory.services import StockService


class InventoryDocumentService:

    @staticmethod
    def _generate_document_number(model_cls, organization, prefix):
        current_year = timezone.now().year
        year_prefix = f"{prefix}-{current_year}-"

        last_doc = model_cls.objects.filter(
            organization=organization,
            document_number__startswith=year_prefix
        ).order_by("-document_number").first()

        if not last_doc:
            return f"{year_prefix}000001"

        try:
            seq_part = last_doc.document_number.split("-")[-1]
            next_seq = int(seq_part) + 1
        except (ValueError, IndexError):
            next_seq = 1

        return f"{year_prefix}{next_seq:06d}"

    # -------------------------------------------------------------------------
    # Goods Received Note (GRN)
    # -------------------------------------------------------------------------
    @classmethod
    @transaction.atomic
    def create_grn(cls, organization, warehouse, received_date, items_data, supplier_name="", notes="", purchase_order=None, user=None):
        if warehouse.organization != organization:
            raise WarehouseOrganizationMismatch()

        doc_number = cls._generate_document_number(GoodsReceivedNote, organization, "GRN")
        grn = GoodsReceivedNote.objects.create(
            organization=organization,
            document_number=doc_number,
            warehouse=warehouse,
            received_date=received_date,
            supplier_name=supplier_name or (purchase_order.supplier.company_name if purchase_order else ""),
            purchase_order=purchase_order,
            notes=notes,
            created_by=user,
            status=DOC_STATUS_DRAFT
        )

        for item_info in items_data:
            product = item_info["product"]
            if product.organization != organization:
                raise WarehouseOrganizationMismatch()

            GoodsReceivedNoteItem.objects.create(
                grn=grn,
                product=product,
                quantity=Decimal(str(item_info["quantity"])),
                unit_cost=Decimal(str(item_info["unit_cost"])) if item_info.get("unit_cost") is not None else None
            )

        return grn

    @staticmethod
    def submit_grn(grn):
        if grn.status != DOC_STATUS_DRAFT:
            raise InvalidDocumentStatusError("Only DRAFT documents can be submitted for review.")
        grn.status = DOC_STATUS_PENDING
        grn.save(update_fields=["status", "updated_at"])
        return grn

    @staticmethod
    def approve_grn(grn, user=None):
        if grn.status not in (DOC_STATUS_DRAFT, DOC_STATUS_PENDING):
            raise InvalidDocumentStatusError("Only DRAFT or PENDING documents can be approved.")
        grn.status = DOC_STATUS_APPROVED
        grn.approved_by = user
        grn.approved_at = timezone.now()
        grn.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return grn

    @staticmethod
    @transaction.atomic
    def complete_grn(grn, user=None):
        from core.exceptions import BusinessRuleError

        if grn.status == DOC_STATUS_COMPLETED:
            raise InvalidDocumentStatusError("This GRN is already completed.")
        if grn.status == DOC_STATUS_CANCELLED:
            raise InvalidDocumentStatusError("Cannot complete a cancelled GRN.")

        po = grn.purchase_order
        if po:
            if po.status not in ("APPROVED", "PARTIAL_RECEIPT"):
                raise BusinessRuleError(f"Cannot receive goods for purchase order in '{po.status}' status.")

            # Validate over-receiving for all items
            for item in grn.items.all():
                po_item = po.items.filter(product=item.product).first()
                if po_item:
                    remaining = po_item.remaining_quantity
                    if Decimal(str(item.quantity)) > remaining:
                        raise BusinessRuleError(
                            f"Cannot receive {item.quantity} units of '{item.product.name}'. Only {remaining} units remain on the purchase order."
                        )

            # Update received quantities
            for item in grn.items.all():
                po_item = po.items.filter(product=item.product).first()
                if po_item:
                    po_item.received_quantity += Decimal(str(item.quantity))
                    po_item.save(update_fields=["received_quantity"])

            # Update PO status
            all_received = all(
                pi.received_quantity >= pi.quantity for pi in po.items.all()
            )
            if all_received:
                po.status = "RECEIVED"
            else:
                po.status = "PARTIAL_RECEIPT"
            po.save(update_fields=["status", "updated_at"])

        for item in grn.items.all():
            StockService.receive(
                product=item.product,
                warehouse=grn.warehouse,
                quantity=item.quantity,
                reference_type="GRN",
                reference_id=grn.id,
                notes=f"GRN completion: {grn.document_number}"
            )

        grn.status = DOC_STATUS_COMPLETED
        grn.completed_by = user
        grn.completed_at = timezone.now()
        grn.save(update_fields=["status", "completed_by", "completed_at", "updated_at"])
        return grn

    @staticmethod
    def cancel_grn(grn):
        if grn.status == DOC_STATUS_COMPLETED:
            raise InvalidDocumentStatusError("Cannot cancel an already COMPLETED document.")
        grn.status = DOC_STATUS_CANCELLED
        grn.save(update_fields=["status", "updated_at"])
        return grn

    # -------------------------------------------------------------------------
    # Goods Issue Note (GIN)
    # -------------------------------------------------------------------------
    @classmethod
    @transaction.atomic
    def create_gin(cls, organization, warehouse, issue_date, items_data, notes="", user=None):
        if warehouse.organization != organization:
            raise WarehouseOrganizationMismatch()

        doc_number = cls._generate_document_number(GoodsIssueNote, organization, "GIN")
        gin = GoodsIssueNote.objects.create(
            organization=organization,
            document_number=doc_number,
            warehouse=warehouse,
            issue_date=issue_date,
            notes=notes,
            created_by=user,
            status=DOC_STATUS_DRAFT
        )

        for item_info in items_data:
            product = item_info["product"]
            if product.organization != organization:
                raise WarehouseOrganizationMismatch()

            GoodsIssueNoteItem.objects.create(
                gin=gin,
                product=product,
                quantity=Decimal(str(item_info["quantity"]))
            )

        return gin

    @staticmethod
    def submit_gin(gin):
        if gin.status != DOC_STATUS_DRAFT:
            raise InvalidDocumentStatusError("Only DRAFT documents can be submitted for review.")
        gin.status = DOC_STATUS_PENDING
        gin.save(update_fields=["status", "updated_at"])
        return gin

    @staticmethod
    def approve_gin(gin, user=None):
        if gin.status not in (DOC_STATUS_DRAFT, DOC_STATUS_PENDING):
            raise InvalidDocumentStatusError("Only DRAFT or PENDING documents can be approved.")
        gin.status = DOC_STATUS_APPROVED
        gin.approved_by = user
        gin.approved_at = timezone.now()
        gin.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return gin

    @staticmethod
    @transaction.atomic
    def complete_gin(gin, user=None):
        if gin.status == DOC_STATUS_COMPLETED:
            raise InvalidDocumentStatusError("This GIN is already completed.")
        if gin.status == DOC_STATUS_CANCELLED:
            raise InvalidDocumentStatusError("Cannot complete a cancelled GIN.")

        for item in gin.items.all():
            StockService.issue(
                product=item.product,
                warehouse=gin.warehouse,
                quantity=item.quantity,
                reference_type="GIN",
                reference_id=gin.id,
                notes=f"GIN completion: {gin.document_number}"
            )

        gin.status = DOC_STATUS_COMPLETED
        gin.completed_by = user
        gin.completed_at = timezone.now()
        gin.save(update_fields=["status", "completed_by", "completed_at", "updated_at"])
        return gin

    @staticmethod
    def cancel_gin(gin):
        if gin.status == DOC_STATUS_COMPLETED:
            raise InvalidDocumentStatusError("Cannot cancel an already COMPLETED document.")
        gin.status = DOC_STATUS_CANCELLED
        gin.save(update_fields=["status", "updated_at"])
        return gin

    # -------------------------------------------------------------------------
    # Stock Transfer Document
    # -------------------------------------------------------------------------
    @classmethod
    @transaction.atomic
    def create_transfer(cls, organization, source_warehouse, destination_warehouse, transfer_date, items_data, notes="", user=None):
        if source_warehouse.organization != organization or destination_warehouse.organization != organization:
            raise WarehouseOrganizationMismatch()

        doc_number = cls._generate_document_number(StockTransferDocument, organization, "TRF")
        transfer_doc = StockTransferDocument.objects.create(
            organization=organization,
            document_number=doc_number,
            source_warehouse=source_warehouse,
            destination_warehouse=destination_warehouse,
            transfer_date=transfer_date,
            notes=notes,
            created_by=user,
            status=DOC_STATUS_DRAFT
        )

        for item_info in items_data:
            product = item_info["product"]
            if product.organization != organization:
                raise WarehouseOrganizationMismatch()

            StockTransferDocumentItem.objects.create(
                transfer=transfer_doc,
                product=product,
                quantity=Decimal(str(item_info["quantity"]))
            )

        return transfer_doc

    @staticmethod
    def submit_transfer(transfer_doc):
        if transfer_doc.status != DOC_STATUS_DRAFT:
            raise InvalidDocumentStatusError("Only DRAFT documents can be submitted for review.")
        transfer_doc.status = DOC_STATUS_PENDING
        transfer_doc.save(update_fields=["status", "updated_at"])
        return transfer_doc

    @staticmethod
    def approve_transfer(transfer_doc, user=None):
        if transfer_doc.status not in (DOC_STATUS_DRAFT, DOC_STATUS_PENDING):
            raise InvalidDocumentStatusError("Only DRAFT or PENDING documents can be approved.")
        transfer_doc.status = DOC_STATUS_APPROVED
        transfer_doc.approved_by = user
        transfer_doc.approved_at = timezone.now()
        transfer_doc.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return transfer_doc

    @staticmethod
    @transaction.atomic
    def complete_transfer(transfer_doc, user=None):
        if transfer_doc.status == DOC_STATUS_COMPLETED:
            raise InvalidDocumentStatusError("This Stock Transfer is already completed.")
        if transfer_doc.status == DOC_STATUS_CANCELLED:
            raise InvalidDocumentStatusError("Cannot complete a cancelled Stock Transfer.")

        for item in transfer_doc.items.all():
            StockService.transfer(
                product=item.product,
                from_warehouse=transfer_doc.source_warehouse,
                to_warehouse=transfer_doc.destination_warehouse,
                quantity=item.quantity,
                reference_type="STOCK_TRANSFER",
                reference_id=transfer_doc.id,
                notes=f"Stock Transfer completion: {transfer_doc.document_number}"
            )

        transfer_doc.status = DOC_STATUS_COMPLETED
        transfer_doc.completed_by = user
        transfer_doc.completed_at = timezone.now()
        transfer_doc.save(update_fields=["status", "completed_by", "completed_at", "updated_at"])
        return transfer_doc

    @staticmethod
    def cancel_transfer(transfer_doc):
        if transfer_doc.status == DOC_STATUS_COMPLETED:
            raise InvalidDocumentStatusError("Cannot cancel an already COMPLETED document.")
        transfer_doc.status = DOC_STATUS_CANCELLED
        transfer_doc.save(update_fields=["status", "updated_at"])
        return transfer_doc

    # -------------------------------------------------------------------------
    # Stock Adjustment Document
    # -------------------------------------------------------------------------
    @classmethod
    @transaction.atomic
    def create_adjustment(cls, organization, warehouse, adjustment_date, items_data, notes="", user=None):
        if warehouse.organization != organization:
            raise WarehouseOrganizationMismatch()

        doc_number = cls._generate_document_number(StockAdjustmentDocument, organization, "ADJ")
        adj = StockAdjustmentDocument.objects.create(
            organization=organization,
            document_number=doc_number,
            warehouse=warehouse,
            adjustment_date=adjustment_date,
            notes=notes,
            created_by=user,
            status=DOC_STATUS_DRAFT
        )

        for item_info in items_data:
            product = item_info["product"]
            if product.organization != organization:
                raise WarehouseOrganizationMismatch()

            sys_qty = StockService.get_balance(product, warehouse=warehouse)
            counted_qty = Decimal(str(item_info["counted_quantity"]))
            diff = counted_qty - sys_qty

            StockAdjustmentDocumentItem.objects.create(
                adjustment=adj,
                product=product,
                system_quantity=sys_qty,
                counted_quantity=counted_qty,
                difference=diff,
                reason=item_info.get("reason") or ""
            )

        return adj

    @staticmethod
    def submit_adjustment(adj):
        if adj.status != DOC_STATUS_DRAFT:
            raise InvalidDocumentStatusError("Only DRAFT documents can be submitted for review.")
        adj.status = DOC_STATUS_PENDING
        adj.save(update_fields=["status", "updated_at"])
        return adj

    @staticmethod
    def approve_adjustment(adj, user=None):
        if adj.status not in (DOC_STATUS_DRAFT, DOC_STATUS_PENDING):
            raise InvalidDocumentStatusError("Only DRAFT or PENDING documents can be approved.")
        adj.status = DOC_STATUS_APPROVED
        adj.approved_by = user
        adj.approved_at = timezone.now()
        adj.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return adj

    @staticmethod
    @transaction.atomic
    def complete_adjustment(adj, user=None):
        if adj.status == DOC_STATUS_COMPLETED:
            raise InvalidDocumentStatusError("This Stock Adjustment is already completed.")
        if adj.status == DOC_STATUS_CANCELLED:
            raise InvalidDocumentStatusError("Cannot complete a cancelled Stock Adjustment.")

        for item in adj.items.all():
            StockService.adjust(
                product=item.product,
                warehouse=adj.warehouse,
                new_quantity=item.counted_quantity,
                reference_type="STOCK_ADJUSTMENT",
                reference_id=adj.id,
                notes=f"Stock Adjustment completion: {adj.document_number}"
            )

        adj.status = DOC_STATUS_COMPLETED
        adj.completed_by = user
        adj.completed_at = timezone.now()
        adj.save(update_fields=["status", "completed_by", "completed_at", "updated_at"])
        return adj

    @staticmethod
    def cancel_adjustment(adj):
        if adj.status == DOC_STATUS_COMPLETED:
            raise InvalidDocumentStatusError("Cannot cancel an already COMPLETED document.")
        adj.status = DOC_STATUS_CANCELLED
        adj.save(update_fields=["status", "updated_at"])
        return adj


class GoodsIssueService:

    @staticmethod
    def _require_permission(user, permission_code):
        if user is None or not user.is_authenticated:
            raise BusinessRuleError("Authentication is required.")
        from invoices.permissions import has_permission
        if not has_permission(user, permission_code):
            raise BusinessRuleError(f"User does not have permission: {permission_code}")

    @classmethod
    def get_invoice_fulfillment(cls, invoice):
        fulfillment = {}

        for invoice_item in invoice.items.select_related("product"):
            if not invoice_item.product_id or not invoice_item.product.is_stockable:
                continue

            issued = (
                GoodsIssueNoteItem.objects
                .filter(
                    gin__invoice=invoice,
                    gin__status=DOC_STATUS_COMPLETED,
                    product=invoice_item.product,
                )
                .aggregate(total=Sum("quantity"))
                .get("total")
                or Decimal("0.00")
            )

            quantity = Decimal(str(invoice_item.qty))

            fulfillment[invoice_item.product_id] = {
                "product": invoice_item.product,
                "invoiced": quantity,
                "issued": issued,
                "remaining": max(
                    Decimal("0.00"),
                    quantity - issued,
                ),
            }

        return fulfillment

    @classmethod
    def validate_against_invoice(cls, gin):
        if not gin.invoice_id:
            return True

        invoice = gin.invoice
        fulfillment = cls.get_invoice_fulfillment(invoice)

        for item in gin.items.select_related("product"):
            data = fulfillment.get(item.product_id)

            if data is None:
                raise BusinessRuleError(
                    f"Product '{item.product.name}' "
                    "does not exist on the invoice."
                )

            requested = Decimal(str(item.quantity))

            if requested > data["remaining"]:
                raise BusinessRuleError(
                    f"Cannot issue {requested} units of "
                    f"'{item.product.name}'. "
                    f"Invoice remaining quantity is "
                    f"{data['remaining']}."
                )

        return True

    @classmethod
    def validate(cls, gin):
        errors = []

        if not gin.organization_id:
            errors.append(
                "Goods Issue Note must belong to an organization."
            )

        if not gin.warehouse_id:
            errors.append(
                "A warehouse is required."
            )

        if gin.invoice_id:
            if gin.invoice.organization_id != gin.organization_id:
                errors.append(
                    "Invoice and Goods Issue Note must belong "
                    "to the same organization."
                )

        items = list(
            gin.items.select_related("product")
        )

        if not items:
            errors.append(
                "Goods Issue Note must contain at least one item."
            )

        seen_products = set()

        for item in items:
            if item.quantity <= 0:
                errors.append(
                    f"Quantity for {item.product.name} must be greater than zero."
                )

            if not item.product.is_stockable:
                errors.append(
                    f"Product '{item.product.name}' "
                    "is not stockable and cannot be issued "
                    "through inventory."
                )

            if item.product.organization_id != gin.organization_id:
                errors.append(
                    f"Product '{item.product.name}' "
                    "does not belong to the GIN organization."
                )

            if item.product.organization_id != gin.warehouse.organization_id:
                errors.append(
                    f"Product '{item.product.name}' "
                    "does not belong to the warehouse organization."
                )

            if item.product_id in seen_products:
                errors.append(
                    f"Product '{item.product.name}' "
                    "appears more than once on this GIN."
                )

            seen_products.add(item.product_id)

        if errors:
            raise BusinessRuleError(
                "Goods Issue Note validation failed: "
                + " ".join(errors)
            )

        cls.validate_against_invoice(gin)

        return True

    @staticmethod
    def _format_stock_shortage_message(shortages):
        parts = []

        for shortage in shortages:
            parts.append(
                f"{shortage['product']} "
                f"(required={Decimal(str(shortage['required'])):.2f}, "
                f"available={Decimal(str(shortage['available'])):.2f}, "
                f"shortage={Decimal(str(shortage['shortage'])):.2f})"
            )

        return (
            "Insufficient stock for: "
            + "; ".join(parts)
        )

    @classmethod
    def check_stock_availability(cls, gin):
        cls.validate(gin)

        shortages = []

        for item in gin.items.select_related("product"):
            available = StockService.get_balance(
                product=item.product,
                warehouse=gin.warehouse,
            )

            required = Decimal(str(item.quantity))

            if available < required:
                shortages.append({
                    "product_id": item.product_id,
                    "product": item.product.name,
                    "required": required,
                    "available": available,
                    "shortage": required - available,
                })

        if shortages:
            raise InsufficientStockError(
                cls._format_stock_shortage_message(shortages)
            )

        return True

    @classmethod
    def check_stock_availability_locked(cls, gin):
        cls.validate(gin)

        shortages = []

        for item in gin.items.select_related("product"):
            inventory_item = (
                InventoryItem.objects
                .select_for_update()
                .filter(
                    organization=gin.organization,
                    product=item.product,
                    warehouse=gin.warehouse,
                    location=None,
                )
                .first()
            )

            available = (
                inventory_item.quantity
                if inventory_item
                else Decimal("0.00")
            )

            required = Decimal(str(item.quantity))

            if available < required:
                shortages.append({
                    "product": item.product.name,
                    "required": required,
                    "available": available,
                    "shortage": required - available,
                })

        if shortages:
            raise InsufficientStockError(
                cls._format_stock_shortage_message(shortages)
            )

        return True

    @classmethod
    @transaction.atomic
    def create_from_invoice(
        cls,
        *,
        invoice,
        warehouse,
        created_by,
        items,
        document_number,
    ):
        if invoice.organization_id != warehouse.organization_id:
            raise WarehouseOrganizationMismatch(
                "Invoice and warehouse must belong to the same organization."
            )

        gin = GoodsIssueNote.objects.create(
            organization=invoice.organization,
            invoice=invoice,
            warehouse=warehouse,
            document_number=document_number,
            issue_date=timezone.localdate(),
            created_by=created_by,
            status=DOC_STATUS_DRAFT,
        )

        for item_data in items:
            GoodsIssueNoteItem.objects.create(
                gin=gin,
                product=item_data["product"],
                quantity=item_data["quantity"],
            )

        cls.validate(gin)

        return gin

    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        organization,
        warehouse,
        document_number,
        issue_date,
        created_by=None,
        notes="",
    ):
        if warehouse.organization_id != organization.id:
            raise BusinessRuleError(
                "Warehouse does not belong to this organization."
            )

        return GoodsIssueNote.objects.create(
            organization=organization,
            warehouse=warehouse,
            document_number=document_number,
            issue_date=issue_date,
            created_by=created_by,
            notes=notes,
            status=DOC_STATUS_DRAFT,
        )

    @classmethod
    @transaction.atomic
    def add_item(
        cls,
        *,
        gin,
        product,
        quantity,
    ):
        if gin.status != DOC_STATUS_DRAFT:
            raise BusinessRuleError(
                "Items can only be added to a draft Goods Issue Note."
            )

        if product.organization_id != gin.organization_id:
            raise BusinessRuleError(
                "Product does not belong to this organization."
            )

        if product.organization_id != gin.warehouse.organization_id:
            raise BusinessRuleError(
                "Product and warehouse belong to different organizations."
            )

        if quantity <= 0:
            raise BusinessRuleError(
                "Issue quantity must be greater than zero."
            )

        return GoodsIssueNoteItem.objects.create(
            gin=gin,
            product=product,
            quantity=quantity,
        )

    @classmethod
    @transaction.atomic
    def submit(cls, gin):
        if gin.status != DOC_STATUS_DRAFT:
            raise BusinessRuleError(
                "Only draft Goods Issue Notes can be submitted."
            )

        cls.validate(gin)

        gin.status = DOC_STATUS_PENDING
        gin.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return gin

    @classmethod
    @transaction.atomic
    def approve(cls, gin, approved_by):
        if gin.status != DOC_STATUS_PENDING:
            raise BusinessRuleError(
                "Only pending Goods Issue Notes can be approved."
            )

        if approved_by is None:
            raise BusinessRuleError(
                "An approving user is required."
            )

        cls._require_permission(approved_by, "gin.approve")

        if gin.created_by_id and gin.created_by_id == approved_by.id:
            raise BusinessRuleError(
                "The user who created this Goods Issue Note cannot approve it."
            )

        cls.check_stock_availability(gin)

        gin.status = DOC_STATUS_APPROVED
        gin.approved_by = approved_by
        gin.approved_at = timezone.now()

        gin.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )

        return gin

    @classmethod
    @transaction.atomic
    def complete(cls, gin, completed_by):
        if gin.status != DOC_STATUS_APPROVED:
            raise BusinessRuleError(
                "Only approved Goods Issue Notes can be completed."
            )

        if completed_by is None:
            raise BusinessRuleError(
                "A completing user is required."
            )

        cls._require_permission(completed_by, "gin.approve")

        cls.check_stock_availability_locked(gin)

        movements = []

        for item in gin.items.select_related("product"):
            movement = StockService.issue(
                product=item.product,
                warehouse=gin.warehouse,
                quantity=item.quantity,
                movement_type=MOVEMENT_TYPE_SALE,
                reference_type="GIN",
                reference_id=gin.id,
                notes=(
                    f"Goods Issue Note "
                    f"{gin.document_number}"
                ),
            )

            movements.append(movement)

        gin.status = DOC_STATUS_COMPLETED
        gin.completed_by = completed_by
        gin.completed_at = timezone.now()

        gin.save(
            update_fields=[
                "status",
                "completed_by",
                "completed_at",
                "updated_at",
            ]
        )

        return gin, movements

    @classmethod
    @transaction.atomic
    def cancel(cls, gin):
        if gin.status in (
            DOC_STATUS_COMPLETED,
            DOC_STATUS_CANCELLED,
        ):
            raise BusinessRuleError(
                "This Goods Issue Note cannot be cancelled."
            )

        gin.status = DOC_STATUS_CANCELLED
        gin.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return gin


