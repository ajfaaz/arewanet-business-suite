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

    @classmethod
    def get_demo_quotation_data(cls, organization):
        from decimal import Decimal
        from datetime import date, timedelta

        today = date.today()
        valid_until = today + timedelta(days=14)

        items = [
            {
                'description': 'Professional Software Development & Architecture',
                'qty': Decimal("2.00"),
                'unit_price': Decimal("100000.00"),
                'total': Decimal("200000.00"),
            },
            {
                'description': 'System Setup, Infrastructure & Cloud Consultation',
                'qty': Decimal("1.00"),
                'unit_price': Decimal("50000.00"),
                'total': Decimal("50000.00"),
            }
        ]

        subtotal = Decimal("250000.00")
        vat_rate = Decimal("7.50")
        vat_amount = Decimal("18750.00")
        discount = Decimal("0.00")
        total = Decimal("268750.00")

        return {
            'is_demo': True,
            'quotation_no': 'QT-DEMO-0001',
            'quotation_date': today,
            'valid_until': valid_until,
            'status': 'DRAFT',
            'customer': {
                'company_name': 'Demo Customer Ltd',
                'name': 'John Doe',
                'email': 'customer@demo.example.com',
                'phone': '+234 800 123 4567',
                'address': '123 Commercial Avenue, Victoria Island, Lagos'
            },
            'items': items,
            'subtotal': subtotal,
            'vat': vat_rate,
            'vat_amount': vat_amount,
            'discount': discount,
            'total': total,
            'notes': 'Thank you for giving us the opportunity to submit this proposal.',
            'terms': '1. Prices are valid for 14 days from issue date.\n2. Payment terms: 50% advance upon confirmation, 50% upon delivery.\n3. All figures in Nigerian Naira (NGN).'
        }

