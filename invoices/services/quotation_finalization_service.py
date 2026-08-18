from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.choices import QuotationStatus
from invoices.models import Quotation
from invoices.services.audit_service import AuditService
from invoices.services.quotation_template_resolver import QuotationTemplateResolver


class QuotationFinalizationService:
    """
    Service responsible for document finalization & issuance governance.
    Locks business data, template choice, sets issued timestamps, and updates lifecycle status.
    """

    @classmethod
    @transaction.atomic
    def finalize(cls, quotation: Quotation, user=None, target_status=QuotationStatus.SENT) -> Quotation:
        # 1. Validate status (Must be in DRAFT state)
        if quotation.status != QuotationStatus.DRAFT:
            raise ValidationError(
                f"Quotation #{quotation.quotation_no} is already finalized with status '{quotation.get_status_display()}' and cannot be issued again."
            )

        # 2. Validate Organization
        if not quotation.organization_id:
            raise ValidationError("Quotation must belong to a valid organization.")

        # 3. Validate Customer
        if not quotation.customer_id:
            raise ValidationError("Quotation must be assigned to a valid customer.")

        # 4. Validate Items (At least 1 item required)
        items = list(quotation.items.all())
        if not items:
            raise ValidationError("Quotation must contain at least one item.")

        # 5. Validate Line Item Quantities and Prices
        for item in items:
            qty = getattr(item, 'qty', getattr(item, 'quantity', Decimal("0")))
            price = getattr(item, 'unit_price', Decimal("0"))
            if qty is None or Decimal(str(qty)) <= Decimal("0"):
                raise ValidationError(f"Line item '{item.description}' must have a quantity greater than zero.")
            if price is None or Decimal(str(price)) < Decimal("0"):
                raise ValidationError(f"Line item '{item.description}' cannot have a negative unit price.")

        # 6. Template Resolution (Keep current template if set; fallback to default active template if unassigned)
        if not quotation.template_id:
            resolved_tpl = QuotationTemplateResolver.resolve(
                organization=quotation.organization,
                quotation=quotation
            )
            if resolved_tpl:
                quotation.template = resolved_tpl

        # 7. Recalculate totals
        from sales.services.quotation_service import QuotationService
        subtotal, vat_amount, total = QuotationService.calculate_totals(
            items,
            vat_rate=quotation.vat,
            discount=quotation.discount
        )
        quotation.subtotal = subtotal
        quotation.total = total

        # 8. Set Timestamps and Issuer
        quotation.issued_at = timezone.now()
        if user and user.is_authenticated:
            quotation.issued_by = user

        # 9. Lifecycle Transition
        quotation.status = target_status
        quotation.save()

        # 10. Audit Logging
        if user and user.is_authenticated:
            ref_no = getattr(quotation, 'quotation_no', f"QTN-{quotation.pk}")
            AuditService.log(
                user,
                f"Issued Quotation {ref_no}",
                reference=ref_no
            )

        return quotation
