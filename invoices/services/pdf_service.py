from django.template.loader import render_to_string
from django.http import HttpResponse

class PDFService:

    @staticmethod
    def generate_invoice_pdf(invoice):
        """
        Generate PDF bytes or HTML render stream for an invoice.
        """
        html_content = render_to_string('invoices/invoice_pdf.html', {'invoice': invoice})
        # If WeasyPrint or another PDF library is installed, render to PDF; otherwise fallback to HTML HttpResponse
        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html_content).write_pdf()
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="Invoice_{invoice.invoice_no}.pdf"'
            return response
        except ImportError:
            return HttpResponse(html_content)

    @staticmethod
    def generate_receipt_pdf(payment):
        """
        Generate PDF bytes or HTML render stream for a payment receipt.
        """
        html_content = render_to_string('payments/receipt_print.html', {'payment': payment})
        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html_content).write_pdf()
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="Receipt_{payment.receipt_no}.pdf"'
            return response
        except ImportError:
            return HttpResponse(html_content)
