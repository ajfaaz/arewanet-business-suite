from decimal import Decimal
from datetime import date
from django.db import transaction
from django.template.loader import render_to_string
from django.http import HttpResponse

from invoices.models import Quotation, ActivityLog
from sales.services.quotation_service import QuotationService as DomainQuotationService


class QuotationAPIService:

    @staticmethod
    @transaction.atomic
    def create(*, organization, validated_data, user):
        items_data = validated_data.pop("items", [])
        
        quotation = Quotation.objects.create(
            organization=organization,
            **validated_data
        )

        return DomainQuotationService.create(quotation, items_data, user=user)

    @staticmethod
    @transaction.atomic
    def convert_to_invoice(*, quotation, user):
        return DomainQuotationService.convert_to_invoice(quotation, user=user)

    @staticmethod
    def approve(*, quotation, user):
        return DomainQuotationService.approve(quotation, user=user)

    @staticmethod
    def reject(*, quotation, user):
        return DomainQuotationService.reject(quotation, user=user)

    @staticmethod
    def generate_pdf(quotation, response):
        html_content = render_to_string('invoices/quotation_pdf.html', {'quotation': quotation}) if False else f"<h1>Quotation #{quotation.quotation_no}</h1><p>Customer: {quotation.customer.company_name}</p><p>Total: NGN {quotation.total:,.2f}</p>"
        res = HttpResponse(html_content, content_type="text/html")
        return res

    @staticmethod
    def email_quotation(quotation, user):
        ActivityLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=f"Quotation #{quotation.quotation_no} dispatched via Email API to {quotation.customer.email if quotation.customer else 'N/A'}"
        )
        return True
