from django.template.loader import render_to_string
from invoices.services.quotation_template_service import QuotationTemplateService


class QuotationTemplateRenderer:

    STYLE_TEMPLATE_MAP = {
        'modern': 'quotations/preview/modern.html',
        'classic': 'quotations/preview/classic.html',
        'minimal': 'quotations/preview/minimal.html',
    }

    def __init__(self, organization=None):
        self.organization = organization

    def render_context(self, quotation, template=None, all_templates=None, all_quotations=None):
        if isinstance(quotation, dict):
            org = self.organization
            items = quotation.get('items', [])
            customer = quotation.get('customer', None)
            is_demo = quotation.get('is_demo', False)
        else:
            org = self.organization or quotation.organization
            items = quotation.items.all() if hasattr(quotation, 'items') else []
            customer = getattr(quotation, 'customer', None)
            is_demo = False

        if isinstance(customer, dict):
            customer_name = customer.get('company_name') or customer.get('name') or 'Valued Customer'
            customer_contact_person = customer.get('contact_person') or customer.get('contact_name') or ''
            customer_address = customer.get('address', '')
            customer_email = customer.get('email', '')
            customer_phone = customer.get('phone', '')
        elif customer:
            customer_name = getattr(customer, 'company_name', None) or 'Valued Customer'
            customer_contact_person = getattr(customer, 'contact_person', None) or getattr(customer, 'contact_name', None) or ''
            customer_address = getattr(customer, 'address', '')
            customer_email = getattr(customer, 'email', '')
            customer_phone = getattr(customer, 'phone', '')
        else:
            customer_name = 'Valued Customer'
            customer_contact_person = ''
            customer_address = ''
            customer_email = ''
            customer_phone = ''

        # Currency Resolution
        currency_code = 'NGN'
        if isinstance(quotation, dict) and quotation.get('currency'):
            currency_code = quotation.get('currency')
        elif hasattr(quotation, 'currency') and getattr(quotation, 'currency', None):
            currency_code = getattr(quotation, 'currency')
        elif org and hasattr(org, 'currency') and org.currency:
            currency_code = org.currency

        currency_symbols = {
            'NGN': '₦',
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'CAD': 'CA$',
            'AUD': 'A$',
        }
        currency_symbol = currency_symbols.get(str(currency_code).upper(), str(currency_code))

        # Terms Resolution
        terms = None
        if isinstance(quotation, dict):
            terms = quotation.get('terms')
        elif hasattr(quotation, 'terms') and quotation.terms:
            terms = quotation.terms

        if not terms and org and hasattr(org, 'terms') and org.terms:
            terms = org.terms

        if not template:
            from invoices.services.quotation_template_resolver import QuotationTemplateResolver
            template = QuotationTemplateResolver.resolve(
                organization=org,
                quotation=quotation if not isinstance(quotation, dict) else None
            )


        raw_style = template.style if template and hasattr(template, 'style') else 'modern'
        style = raw_style if raw_style in self.STYLE_TEMPLATE_MAP else 'modern'

        context = {
            'quotation': quotation,
            'organization': org,
            'customer': customer,
            'customer_name': customer_name,
            'customer_contact_person': customer_contact_person,
            'customer_address': customer_address,
            'customer_email': customer_email,
            'customer_phone': customer_phone,
            'currency_code': currency_code,
            'currency_symbol': currency_symbol,
            'terms': terms,
            'items': items,
            'template': template,
            'style': style,
            'is_demo': is_demo,
            'all_templates': all_templates or [],
            'all_quotations': all_quotations or [],
        }

        return context

    def render(self, quotation, template=None, request=None, extra_context=None):
        context = self.render_context(quotation, template=template)
        if extra_context:
            context.update(extra_context)

        style = context.get('style', 'modern')
        template_name = self.STYLE_TEMPLATE_MAP.get(style, self.STYLE_TEMPLATE_MAP['modern'])

        return render_to_string(template_name, context, request=request)

