import io
import os
from django.conf import settings
from django.template.loader import render_to_string
from xhtml2pdf import pisa

from invoices.services.quotation_template_resolver import QuotationTemplateResolver
from invoices.services.template_renderer import QuotationTemplateRenderer


def fetch_resources(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can resolve local media & static assets.
    """
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    elif uri.startswith(settings.STATIC_URL):
        static_dir = getattr(settings, 'STATIC_ROOT', None) or (settings.BASE_DIR / 'static')
        path = os.path.join(str(static_dir), uri.replace(settings.STATIC_URL, ""))
    else:
        path = os.path.join(str(settings.BASE_DIR), uri)

    if os.path.isfile(path):
        return path
    return uri


class QuotationPDFService:
    """
    Service responsible for converting Quotation documents into PDF binaries.
    Enforces single-source-of-truth HTML rendering by delegating context compilation
    and template resolution to QuotationTemplateRenderer.
    """

    @classmethod
    def generate(cls, quotation, template=None, request=None) -> bytes:
        org = getattr(quotation, 'organization', None)

        # Step 1: Resolve Quotation Template
        resolved_template = QuotationTemplateResolver.resolve(
            organization=org,
            quotation=quotation if hasattr(quotation, 'pk') else None,
            requested_template=template
        )

        # Step 2: Render HTML string via QuotationTemplateRenderer
        renderer = QuotationTemplateRenderer(organization=org)
        context = renderer.render_context(quotation, template=resolved_template)
        context['is_pdf'] = True
        context['base_template'] = 'quotations/preview/base_pdf.html'

        style = context.get('style', 'modern')
        template_name = QuotationTemplateRenderer.STYLE_TEMPLATE_MAP.get(
            style,
            QuotationTemplateRenderer.STYLE_TEMPLATE_MAP['modern']
        )

        html_content = render_to_string(template_name, context, request=request)

        # Step 3: Convert HTML to PDF bytes using xhtml2pdf pisa
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(
            src=html_content,
            dest=pdf_buffer,
            link_callback=fetch_resources
        )

        if pisa_status.err:
            raise RuntimeError(f"PDF rendering error: {pisa_status.err}")

        return pdf_buffer.getvalue()
