from invoices.models import QuotationTemplate


class QuotationTemplateService:

    def __init__(self, organization):
        self.organization = organization

    def get_templates(self, include_inactive=False):
        qs = QuotationTemplate.objects.filter(organization=self.organization)
        if not include_inactive:
            qs = qs.filter(is_active=True)
        return qs

    def get_template(self, template_id, active_only=True):
        qs = QuotationTemplate.objects.filter(
            id=template_id,
            organization=self.organization
        )
        if active_only:
            qs = qs.filter(is_active=True)
        return qs.first()

    def get_default_template(self):
        default_tpl = QuotationTemplate.objects.filter(
            organization=self.organization,
            is_active=True,
            is_default=True
        ).first()

        if not default_tpl:
            # Fallback to first active template or auto-create default Modern Quotation template
            default_tpl = QuotationTemplate.objects.filter(
                organization=self.organization,
                is_active=True
            ).first()

            if not default_tpl:
                default_tpl = QuotationTemplate.objects.create(
                    organization=self.organization,
                    name="Modern Quotation",
                    style="modern",
                    description="Default modern template format",
                    is_active=True,
                    is_default=True
                )
        return default_tpl

    def set_default_template(self, template_id):
        template = self.get_template(template_id, active_only=True)
        if not template:
            raise ValueError("Template not found or inactive for this organization.")

        template.is_default = True
        template.save()
        return template

    def create_template(self, name, style='modern', description='', is_default=False):
        return QuotationTemplate.objects.create(
            organization=self.organization,
            name=name,
            style=style,
            description=description,
            is_active=True,
            is_default=is_default
        )
