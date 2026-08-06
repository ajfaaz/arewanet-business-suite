import os
from decimal import Decimal
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_REGULAR = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
FONT_ITALIC = 'Helvetica-Oblique'

arial_paths = {
    'Arial': 'C:/Windows/Fonts/arial.ttf',
    'Arial-Bold': 'C:/Windows/Fonts/arialbd.ttf',
    'Arial-Italic': 'C:/Windows/Fonts/ariali.ttf',
}

if all(os.path.exists(path) for path in arial_paths.values()):
    try:
        for name, path in arial_paths.items():
            pdfmetrics.registerFont(TTFont(name, path))
        FONT_REGULAR = 'Arial'
        FONT_BOLD = 'Arial-Bold'
        FONT_ITALIC = 'Arial-Italic'
    except Exception:
        pass


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor('#E5E7EB'))
            self.setLineWidth(0.5)
            self.line(36, 756, 576, 756)

        self.setFont(FONT_ITALIC, 9)
        self.setFillColor(colors.HexColor('#777777'))
        self.drawString(36, 30, "Thank you for your business!")

        self.setFont(FONT_REGULAR, 9)
        self.drawRightString(576, 30, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def format_naira(amount):
    try:
        val = float(amount)
        return f"₦{val:,.2f}"
    except (ValueError, TypeError):
        return "₦0.00"


class PDFService:

    @classmethod
    def _create_base_styles(cls):
        NAVY = colors.HexColor("#0F3F62")
        MUTED = colors.HexColor("#6c757d")
        DARK = colors.HexColor("#212529")

        return {
            'org_title': ParagraphStyle('OrgTitle', fontName=FONT_BOLD, fontSize=12, leading=14, textColor=DARK),
            'org_info': ParagraphStyle('OrgInfo', fontName=FONT_REGULAR, fontSize=9, leading=13, textColor=MUTED),
            'doc_header': ParagraphStyle('DocHeader', fontName=FONT_BOLD, fontSize=22, leading=24, alignment=2, textColor=NAVY),
            'meta_label': ParagraphStyle('MetaLabel', fontName=FONT_BOLD, fontSize=9, leading=13, textColor=NAVY),
            'meta_val': ParagraphStyle('MetaVal', fontName=FONT_REGULAR, fontSize=9, leading=13, alignment=2, textColor=DARK),
            'section_heading': ParagraphStyle('SecHead', fontName=FONT_BOLD, fontSize=9, leading=11, textColor=MUTED),
            'client_name': ParagraphStyle('ClientName', fontName=FONT_BOLD, fontSize=11, leading=14, textColor=NAVY),
            'body_text': ParagraphStyle('BodyTextCustom', fontName=FONT_REGULAR, fontSize=9, leading=13, textColor=DARK),
            'th': ParagraphStyle('TH', fontName=FONT_BOLD, fontSize=9, leading=11, textColor=colors.white),
            'td_sn': ParagraphStyle('TDSN', fontName=FONT_REGULAR, fontSize=9, leading=12, alignment=0, textColor=DARK),
            'td_desc': ParagraphStyle('TDDesc', fontName=FONT_REGULAR, fontSize=9, leading=13, textColor=DARK),
            'td_right': ParagraphStyle('TDRight', fontName=FONT_REGULAR, fontSize=9, leading=12, alignment=2, textColor=DARK),
            'pay_title': ParagraphStyle('PayTitle', fontName=FONT_BOLD, fontSize=10, leading=12, textColor=NAVY),
            'pay_body': ParagraphStyle('PayBody', fontName=FONT_REGULAR, fontSize=8.5, leading=12, textColor=DARK),
            'total_label': ParagraphStyle('TotalLabel', fontName=FONT_REGULAR, fontSize=9.5, leading=13, textColor=DARK),
            'total_val': ParagraphStyle('TotalVal', fontName=FONT_REGULAR, fontSize=9.5, leading=13, alignment=2, textColor=DARK),
            'banner_label': ParagraphStyle('BannerLabel', fontName=FONT_BOLD, fontSize=11, leading=13, textColor=colors.white),
            'banner_val': ParagraphStyle('BannerVal', fontName=FONT_BOLD, fontSize=11, leading=13, alignment=2, textColor=colors.white),
        }

    @classmethod
    def generate_invoice(cls, invoice, response):
        from invoices.utils.pdf_generator import generate_invoice_pdf
        return generate_invoice_pdf(response, invoice)

    @classmethod
    def generate_receipt(cls, payment, response):
        from sales.payments.services import PaymentService
        return PaymentService.generate_receipt_pdf(payment, response)

    @classmethod
    def generate_credit_note(cls, credit_note, response):
        doc = SimpleDocTemplate(response, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=54)
        styles = cls._create_base_styles()
        story = []
        NAVY = colors.HexColor("#0F3F62")
        org = credit_note.organization
        cust = credit_note.customer

        # Header
        left_flow = [
            Paragraph(org.name if org else "ArewaNet Ventures", styles['org_title']),
            Spacer(1, 4),
            Paragraph(f"Phone: {getattr(org, 'phone', '09017862785')}", styles['org_info']),
            Paragraph(f"Email: {getattr(org, 'email', 'info@arewanetventures.com')}", styles['org_info']),
        ]

        meta_table_data = [
            [Paragraph("Credit Note #:", styles['meta_label']), Paragraph(credit_note.credit_note_no, styles['meta_val'])],
            [Paragraph("Invoice #:", styles['meta_label']), Paragraph(credit_note.invoice.invoice_no, styles['meta_val'])],
            [Paragraph("Date:", styles['meta_label']), Paragraph(credit_note.created_at.strftime("%B %d, %Y"), styles['meta_val'])],
            [Paragraph("Status:", styles['meta_label']), Paragraph(credit_note.get_status_display(), styles['meta_val'])],
        ]
        meta_table = Table(meta_table_data, colWidths=[90, 130])

        right_flow = [
            Paragraph("CREDIT NOTE", styles['doc_header']),
            Spacer(1, 8),
            meta_table
        ]

        header_table = Table([[left_flow, right_flow]], colWidths=[270, 270])
        story.append(header_table)
        story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=15, spaceBefore=5))

        # Bill to
        cust_flow = [
            Paragraph("CREDIT ISSUED TO:", styles['section_heading']),
            Spacer(1, 4),
            Paragraph(cust.company_name, styles['client_name']),
            Paragraph(cust.email or "", styles['body_text']),
        ]
        story.append(Table([[cust_flow, []]], colWidths=[270, 270]))
        story.append(Spacer(1, 15))

        # Details Table
        table_data = [
            [Paragraph("S/N", styles['th']), Paragraph("REASON / DESCRIPTION", styles['th']), Paragraph("INVOICE REF", styles['th']), Paragraph("AMOUNT", styles['th'])],
            [Paragraph("1", styles['td_sn']), Paragraph(credit_note.reason, styles['td_desc']), Paragraph(credit_note.invoice.invoice_no, styles['td_sn']), Paragraph(format_naira(credit_note.amount), styles['td_right'])]
        ]
        items_table = Table(table_data, colWidths=[30, 270, 100, 140], repeatRows=1)
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 20))

        # Total
        due_banner_table = Table([[
            Paragraph("Total Credit Amount:", styles['banner_label']),
            Paragraph(format_naira(credit_note.amount), styles['banner_val'])
        ]], colWidths=[140, 130])
        due_banner_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), NAVY),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(Table([[[], due_banner_table]], colWidths=[270, 270]))

        doc.build(story, canvasmaker=NumberedCanvas)

    @classmethod
    def generate_debit_note(cls, debit_note, response):
        doc = SimpleDocTemplate(response, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=54)
        styles = cls._create_base_styles()
        story = []
        NAVY = colors.HexColor("#0F3F62")
        org = debit_note.organization
        cust = debit_note.customer

        left_flow = [
            Paragraph(org.name if org else "ArewaNet Ventures", styles['org_title']),
            Spacer(1, 4),
            Paragraph(f"Phone: {getattr(org, 'phone', '09017862785')}", styles['org_info']),
            Paragraph(f"Email: {getattr(org, 'email', 'info@arewanetventures.com')}", styles['org_info']),
        ]

        meta_table_data = [
            [Paragraph("Debit Note #:", styles['meta_label']), Paragraph(debit_note.debit_note_no, styles['meta_val'])],
            [Paragraph("Invoice #:", styles['meta_label']), Paragraph(debit_note.invoice.invoice_no, styles['meta_val'])],
            [Paragraph("Date:", styles['meta_label']), Paragraph(debit_note.created_at.strftime("%B %d, %Y"), styles['meta_val'])],
            [Paragraph("Status:", styles['meta_label']), Paragraph(debit_note.get_status_display(), styles['meta_val'])],
        ]
        meta_table = Table(meta_table_data, colWidths=[90, 130])

        right_flow = [
            Paragraph("DEBIT NOTE", styles['doc_header']),
            Spacer(1, 8),
            meta_table
        ]

        header_table = Table([[left_flow, right_flow]], colWidths=[270, 270])
        story.append(header_table)
        story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=15, spaceBefore=5))

        cust_flow = [
            Paragraph("DEBIT ISSUED TO:", styles['section_heading']),
            Spacer(1, 4),
            Paragraph(cust.company_name, styles['client_name']),
            Paragraph(cust.email or "", styles['body_text']),
        ]
        story.append(Table([[cust_flow, []]], colWidths=[270, 270]))
        story.append(Spacer(1, 15))

        table_data = [
            [Paragraph("S/N", styles['th']), Paragraph("REASON / ADJUSTMENT", styles['th']), Paragraph("INVOICE REF", styles['th']), Paragraph("AMOUNT", styles['th'])],
            [Paragraph("1", styles['td_sn']), Paragraph(debit_note.reason, styles['td_desc']), Paragraph(debit_note.invoice.invoice_no, styles['td_sn']), Paragraph(format_naira(debit_note.amount), styles['td_right'])]
        ]
        items_table = Table(table_data, colWidths=[30, 270, 100, 140], repeatRows=1)
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 20))

        due_banner_table = Table([[
            Paragraph("Total Debit Amount:", styles['banner_label']),
            Paragraph(format_naira(debit_note.amount), styles['banner_val'])
        ]], colWidths=[140, 130])
        due_banner_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), NAVY),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(Table([[[], due_banner_table]], colWidths=[270, 270]))

        doc.build(story, canvasmaker=NumberedCanvas)

    @classmethod
    def generate_statement(cls, statement_data, response):
        doc = SimpleDocTemplate(response, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=54)
        styles = cls._create_base_styles()
        story = []
        NAVY = colors.HexColor("#0F3F62")
        org = statement_data['organization']
        cust = statement_data['customer']

        left_flow = [
            Paragraph(org.name if org else "ArewaNet Ventures", styles['org_title']),
            Spacer(1, 4),
            Paragraph(f"Phone: {getattr(org, 'phone', '09017862785')}", styles['org_info']),
            Paragraph(f"Email: {getattr(org, 'email', 'info@arewanetventures.com')}", styles['org_info']),
        ]

        meta_table_data = [
            [Paragraph("Statement Date:", styles['meta_label']), Paragraph(statement_data['generated_at'].strftime("%B %d, %Y"), styles['meta_val'])],
            [Paragraph("Opening Balance:", styles['meta_label']), Paragraph(format_naira(statement_data['opening_balance']), styles['meta_val'])],
            [Paragraph("Closing Balance:", styles['meta_label']), Paragraph(format_naira(statement_data['closing_balance']), styles['meta_val'])],
        ]
        meta_table = Table(meta_table_data, colWidths=[110, 110])

        right_flow = [
            Paragraph("ACCOUNT STATEMENT", styles['doc_header']),
            Spacer(1, 8),
            meta_table
        ]

        header_table = Table([[left_flow, right_flow]], colWidths=[270, 270])
        story.append(header_table)
        story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=15, spaceBefore=5))

        cust_flow = [
            Paragraph("CUSTOMER INFORMATION:", styles['section_heading']),
            Spacer(1, 4),
            Paragraph(cust.company_name, styles['client_name']),
            Paragraph(cust.email or "", styles['body_text']),
        ]
        story.append(Table([[cust_flow, []]], colWidths=[270, 270]))
        story.append(Spacer(1, 15))

        table_data = [
            [Paragraph("DATE", styles['th']), Paragraph("REF #", styles['th']), Paragraph("DESCRIPTION", styles['th']), Paragraph("DEBIT (₦)", styles['th']), Paragraph("CREDIT (₦)", styles['th']), Paragraph("BALANCE (₦)", styles['th'])]
        ]

        for tx in statement_data['transactions']:
            dt_str = tx['date'].strftime("%Y-%m-%d") if hasattr(tx['date'], 'strftime') else str(tx['date'])
            table_data.append([
                Paragraph(dt_str, styles['td_sn']),
                Paragraph(tx['reference'], styles['td_sn']),
                Paragraph(tx['description'], styles['td_desc']),
                Paragraph(format_naira(tx['debit']) if tx['debit'] else "-", styles['td_right']),
                Paragraph(format_naira(tx['credit']) if tx['credit'] else "-", styles['td_right']),
                Paragraph(format_naira(tx['running_balance']), styles['td_right']),
            ])

        items_table = Table(table_data, colWidths=[65, 80, 165, 75, 75, 80], repeatRows=1)
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 20))

        closing_table = Table([[
            Paragraph("Closing Outstanding Balance:", styles['banner_label']),
            Paragraph(format_naira(statement_data['closing_balance']), styles['banner_val'])
        ]], colWidths=[160, 130])
        closing_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), NAVY),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(Table([[[], closing_table]], colWidths=[250, 290]))

        doc.build(story, canvasmaker=NumberedCanvas)
