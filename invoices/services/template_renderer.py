from invoices.services.quotation_template_service import QuotationTemplateService


class QuotationTemplateRenderer:

    def __init__(self, organization=None):
        self.organization = organization

    def render_context(self, quotation, template=None):
        org = self.organization or quotation.organization

        if not template:
            service = QuotationTemplateService(organization=org)
            template = service.get_default_template()

        items = quotation.items.all() if hasattr(quotation, 'items') else []

        context = {
            'quotation': quotation,
            'organization': org,
            'customer': getattr(quotation, 'customer', None),
            'items': items,
            'template': template,
            'style': template.style if template else 'modern',
        }

        return context
