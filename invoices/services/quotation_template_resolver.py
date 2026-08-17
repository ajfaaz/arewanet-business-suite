from invoices.models import QuotationTemplate


class QuotationTemplateResolver:
    """
    Service responsible for resolving the appropriate QuotationTemplate
    for a given quotation or request context, preserving historical stability.

    Priority order:
    1. Explicitly requested template instance/ID (validated for current organization & active status).
    2. Saved quotation.template reference (if set and belongs to active organization).
    3. Active Organization Default Template (is_default=True, is_active=True).
    4. Any active template for the organization.
    """

    @classmethod
    def resolve(cls, organization, quotation=None, requested_template=None):
        if not organization:
            return None

        # Priority 1: Explicitly requested template (e.g. preview override or form parameter)
        if requested_template:
            if isinstance(requested_template, QuotationTemplate):
                if requested_template.organization_id == organization.id and requested_template.is_active:
                    return requested_template
            else:
                try:
                    tpl = QuotationTemplate.objects.get(
                        id=requested_template,
                        organization=organization,
                        is_active=True
                    )
                    return tpl
                except (QuotationTemplate.DoesNotExist, ValueError, TypeError):
                    pass

        # Priority 2: Saved quotation.template reference
        if quotation and getattr(quotation, 'template_id', None):
            tpl = quotation.template
            if tpl and tpl.organization_id == organization.id:
                return tpl

        # Priority 3: Organization Default Template
        default_tpl = QuotationTemplate.objects.filter(
            organization=organization,
            is_default=True,
            is_active=True
        ).first()
        if default_tpl:
            return default_tpl

        # Priority 4: Any active template for organization
        return QuotationTemplate.objects.filter(
            organization=organization,
            is_active=True
        ).first()
