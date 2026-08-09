from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from core.exceptions import InvalidDocumentStatusError, WarehouseOrganizationMismatch
from inventory.models import (
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
