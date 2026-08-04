import os
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    HRFlowable,
    KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Arial TTF fonts if available on Windows to support native Naira '₦' character
FONT_REGULAR = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
FONT_ITALIC = 'Helvetica-Oblique'
FONT_BOLD_ITALIC = 'Helvetica-BoldOblique'

arial_paths = {
    'Arial': 'C:/Windows/Fonts/arial.ttf',
    'Arial-Bold': 'C:/Windows/Fonts/arialbd.ttf',
    'Arial-Italic': 'C:/Windows/Fonts/ariali.ttf',
    'Arial-BoldItalic': 'C:/Windows/Fonts/arialbi.ttf'
}

if all(os.path.exists(path) for path in arial_paths.values()):
    try:
        for name, path in arial_paths.items():
            pdfmetrics.registerFont(TTFont(name, path))
        FONT_REGULAR = 'Arial'
        FONT_BOLD = 'Arial-Bold'
        FONT_ITALIC = 'Arial-Italic'
        FONT_BOLD_ITALIC = 'Arial-BoldItalic'
    except Exception:
        pass


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute total pages and draw footer on all pages.
    """
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
        
        # Draw top rule if page > 1 (multi-page document)
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor('#E5E7EB'))
            self.setLineWidth(0.5)
            self.line(36, 756, 576, 756)
            
        # Draw bottom footer rule & text
        self.setFont(FONT_ITALIC, 9)
        self.setFillColor(colors.HexColor('#777777'))
        self.drawString(36, 30, "Thank you for your business!")
        
        self.setFont(FONT_REGULAR, 9)
        self.drawRightString(576, 30, f"Page {self._pageNumber}")
        
        self.restoreState()


def format_naira(amount):
    """Helper to format currency as Naira with commas and 2 decimals."""
    try:
        val = float(amount)
        return f"₦{val:,.2f}"
    except (ValueError, TypeError):
        return f"₦0.00"


def generate_invoice_pdf(response, invoice, organization=None):
    if organization is None:
        organization = invoice.organization

    doc = SimpleDocTemplate(
        response,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    story = []
    TOTAL_WIDTH = 540  # 612 - 72

    # --- Color Palette ---
    PRIMARY_NAVY = colors.HexColor("#0F3F62")
    TEXT_MUTED = colors.HexColor("#6c757d")
    TEXT_DARK = colors.HexColor("#212529")
    BG_LIGHT = colors.HexColor("#F8F9FA")
    BORDER_LIGHT = colors.HexColor("#E5E7EB")
    COLOR_RED = colors.HexColor("#D9534F")
    COLOR_GREEN = colors.HexColor("#28A745")
    COLOR_ORANGE = colors.HexColor("#F0AD4E")

    # --- Typography Styles ---
    style_org_title = ParagraphStyle(
        'OrgTitle',
        fontName=FONT_BOLD,
        fontSize=12,
        leading=14,
        textColor=TEXT_DARK
    )

    style_org_info = ParagraphStyle(
        'OrgInfo',
        fontName=FONT_REGULAR,
        fontSize=9,
        leading=13,
        textColor=TEXT_MUTED
    )

    style_inv_header = ParagraphStyle(
        'InvHeader',
        fontName=FONT_BOLD,
        fontSize=24,
        leading=26,
        alignment=2,  # Right
        textColor=PRIMARY_NAVY
    )

    style_meta_label = ParagraphStyle(
        'MetaLabel',
        fontName=FONT_BOLD,
        fontSize=9,
        leading=13,
        textColor=PRIMARY_NAVY
    )

    style_meta_val = ParagraphStyle(
        'MetaVal',
        fontName=FONT_REGULAR,
        fontSize=9,
        leading=13,
        alignment=2,  # Right
        textColor=TEXT_DARK
    )

    style_section_heading = ParagraphStyle(
        'SectionHeading',
        fontName=FONT_BOLD,
        fontSize=9,
        leading=11,
        textColor=TEXT_MUTED
    )

    style_client_name = ParagraphStyle(
        'ClientName',
        fontName=FONT_BOLD,
        fontSize=11,
        leading=14,
        textColor=PRIMARY_NAVY
    )

    style_body_text = ParagraphStyle(
        'BodyTextCustom',
        fontName=FONT_REGULAR,
        fontSize=9,
        leading=13,
        textColor=TEXT_DARK
    )

    style_th = ParagraphStyle(
        'TH',
        fontName=FONT_BOLD,
        fontSize=9,
        leading=11,
        textColor=colors.white
    )

    style_td_sn = ParagraphStyle(
        'TDSN',
        fontName=FONT_REGULAR,
        fontSize=9,
        leading=12,
        alignment=0,
        textColor=TEXT_DARK
    )

    style_td_desc_title = ParagraphStyle(
        'TDDescTitle',
        fontName=FONT_BOLD,
        fontSize=9,
        leading=13,
        textColor=TEXT_DARK
    )

    style_td_desc_sub = ParagraphStyle(
        'TDDescSub',
        fontName=FONT_REGULAR,
        fontSize=8,
        leading=11,
        textColor=TEXT_MUTED
    )

    style_td_right = ParagraphStyle(
        'TDRight',
        fontName=FONT_REGULAR,
        fontSize=9,
        leading=12,
        alignment=2,  # Right
        textColor=TEXT_DARK
    )

    style_pay_title = ParagraphStyle(
        'PayTitle',
        fontName=FONT_BOLD,
        fontSize=10,
        leading=12,
        textColor=PRIMARY_NAVY
    )

    style_pay_body = ParagraphStyle(
        'PayBody',
        fontName=FONT_REGULAR,
        fontSize=8.5,
        leading=12,
        textColor=TEXT_DARK
    )

    style_total_label = ParagraphStyle(
        'TotalLabel',
        fontName=FONT_REGULAR,
        fontSize=9.5,
        leading=13,
        textColor=TEXT_DARK
    )

    style_total_val = ParagraphStyle(
        'TotalVal',
        fontName=FONT_REGULAR,
        fontSize=9.5,
        leading=13,
        alignment=2,
        textColor=TEXT_DARK
    )

    style_due_banner_label = ParagraphStyle(
        'DueBannerLabel',
        fontName=FONT_BOLD,
        fontSize=11,
        leading=13,
        textColor=colors.white
    )

    style_due_banner_val = ParagraphStyle(
        'DueBannerVal',
        fontName=FONT_BOLD,
        fontSize=11,
        leading=13,
        alignment=2,
        textColor=colors.white
    )

    # 1. HEADER SECTION
    # Left Block: Logo + Org Info
    left_flow = []
    org_name = organization.name if organization else "ArewaNet Ventures"
    org_phone = organization.phone if (organization and organization.phone) else "09017862785"
    org_email = organization.email if (organization and organization.email) else "info@arewanetventures.com"
    org_website = organization.website if (organization and organization.website) else "arewanetventures.com"

    if organization and organization.logo and hasattr(organization.logo, 'path') and os.path.exists(organization.logo.path):
        try:
            img = Image(organization.logo.path, width=160, height=50)
            img.hAlign = 'LEFT'
            left_flow.append(img)
            left_flow.append(Spacer(1, 6))
        except Exception:
            left_flow.append(Paragraph(org_name, style_org_title))
            left_flow.append(Spacer(1, 4))
    else:
        left_flow.append(Paragraph(org_name, style_org_title))
        left_flow.append(Spacer(1, 4))

    left_flow.append(Paragraph(f"Phone: {org_phone}", style_org_info))
    left_flow.append(Paragraph(f"Email: {org_email}", style_org_info))
    left_flow.append(Paragraph(f"Website: {org_website}", style_org_info))

    # Right Block: INVOICE Title + Metadata Table
    status_str = (invoice.status or "UNPAID").upper()
    if status_str == 'PAID':
        status_html = f'<font color="{COLOR_GREEN.hexval()}"><b>PAID</b></font>'
    elif status_str in ['UNPAID', 'OVERDUE']:
        status_html = f'<font color="{COLOR_RED.hexval()}"><b>{status_str}</b></font>'
    else:
        status_html = f'<font color="{COLOR_ORANGE.hexval()}"><b>{status_str}</b></font>'

    inv_date_str = invoice.invoice_date.strftime("%B %d, %Y") if hasattr(invoice.invoice_date, 'strftime') else str(invoice.invoice_date)
    due_date_str = invoice.due_date.strftime("%B %d, %Y") if hasattr(invoice.due_date, 'strftime') else str(invoice.due_date)

    meta_table_data = [
        [Paragraph("Invoice No:", style_meta_label), Paragraph(str(invoice.invoice_no), style_meta_val)],
        [Paragraph("Date:", style_meta_label), Paragraph(inv_date_str, style_meta_val)],
        [Paragraph("Due Date:", style_meta_label), Paragraph(due_date_str, style_meta_val)],
        [Paragraph("Status:", style_meta_label), Paragraph(status_html, style_meta_val)],
    ]

    meta_table = Table(meta_table_data, colWidths=[80, 140])
    meta_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    right_flow = [
        Paragraph("INVOICE", style_inv_header),
        Spacer(1, 8),
        meta_table
    ]

    header_table = Table([[left_flow, right_flow]], colWidths=[270, 270])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    story.append(header_table)
    story.append(Spacer(1, 10))

    # Dark Accent Line
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY_NAVY, spaceAfter=15, spaceBefore=5))

    # 2. BILL TO & PROJECT CONTEXT SECTION
    # Left: Bill To
    cust = invoice.customer
    bill_to_flow = [
        Paragraph("BILL TO:", style_section_heading),
        Spacer(1, 4),
        Paragraph(cust.company_name if cust else "", style_client_name),
    ]

    if cust and cust.contact_person:
        bill_to_flow.append(Paragraph(cust.contact_person, style_body_text))

    if cust and cust.address:
        lines = [line.strip() for line in cust.address.split('\n') if line.strip()]
        for line in lines:
            bill_to_flow.append(Paragraph(line, style_body_text))

    # Right: Project Context
    proj_name = invoice.project_name if invoice.project_name else ""
    deploy_phase = invoice.deployment_phase if invoice.deployment_phase else ""

    proj_flow = [
        Paragraph("PROJECT CONTEXT:", style_section_heading),
        Spacer(1, 4),
        Paragraph(f"<b>Project:</b> {proj_name}", style_body_text),
        Spacer(1, 2),
        Paragraph(f"<b>Deployment Phase:</b> {deploy_phase}", style_body_text),
    ]

    context_table = Table([[bill_to_flow, proj_flow]], colWidths=[270, 270])
    context_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    story.append(context_table)
    story.append(Spacer(1, 18))

    # 3. ITEMS TABLE
    col_widths = [30, 230, 45, 40, 95, 100]

    table_data = [[
        Paragraph("S/N", style_th),
        Paragraph("ITEM DESCRIPTION", style_th),
        Paragraph("UNIT", style_th),
        Paragraph("QTY", style_th),
        Paragraph("UNIT PRICE", style_th),
        Paragraph("TOTAL", style_th)
    ]]

    for idx, item in enumerate(invoice.items.all(), start=1):
        raw_desc = str(item.description).strip()
        lines = [l.strip() for l in raw_desc.split('\n') if l.strip()]
        if lines:
            title_text = lines[0]
            sub_text = " ".join(lines[1:]) if len(lines) > 1 else ""
        else:
            title_text = ""
            sub_text = ""

        desc_flow = [Paragraph(title_text, style_td_desc_title)]
        if sub_text:
            desc_flow.append(Spacer(1, 2))
            desc_flow.append(Paragraph(sub_text, style_td_desc_sub))

        if item.unit_price == 0 or ("sla" in raw_desc.lower() or "included" in raw_desc.lower()) and item.unit_price == 0:
            unit_price_str = "Included"
        else:
            unit_price_str = format_naira(item.unit_price)

        total_str = format_naira(item.total)
        unit_str = str(item.unit or "-")

        table_data.append([
            Paragraph(str(idx), style_td_sn),
            desc_flow,
            Paragraph(unit_str, style_td_sn),
            Paragraph(str(item.qty), style_td_sn),
            Paragraph(unit_price_str, style_td_right),
            Paragraph(total_str, style_td_right)
        ])

    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_NAVY),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'LEFT'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
    ]

    for r in range(1, len(table_data)):
        if r % 2 == 0:
            t_style.append(('BACKGROUND', (0, r), (-1, r), BG_LIGHT))

    items_table.setStyle(TableStyle(t_style))
    story.append(items_table)
    story.append(Spacer(1, 18))

    # 4. PAYMENT INSTRUCTIONS & FINANCIAL TOTALS
    bank_name = organization.bank_name if (organization and organization.bank_name) else "[Insert Bank Name, e.g., GTBank]"
    account_name = organization.account_name if (organization and organization.account_name) else (organization.name if organization else "ArewaNet Ventures")
    account_no = organization.account_number if (organization and organization.account_number) else "[Insert 10-Digit Account Number]"

    pay_details = [
        Paragraph("PAYMENT INSTRUCTIONS", style_pay_title),
        Spacer(1, 4),
        Paragraph("Please execute bank transfers directly using the details below:", style_pay_body),
        Spacer(1, 6),
        Paragraph(f"<b>Bank Name:</b> {bank_name}", style_pay_body),
        Paragraph(f"<b>Account Name:</b> {account_name}", style_pay_body),
        Paragraph(f"<b>Account No:</b> {account_no}", style_pay_body),
    ]

    pay_table = Table([[pay_details]], colWidths=[250])
    pay_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('LINEBEFORE', (0, 0), (0, -1), 3.5, PRIMARY_NAVY),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))

    vat_rate = float(invoice.vat or 0)
    vat_amount = (float(invoice.subtotal or 0) * vat_rate) / 100.0
    vat_label_str = f"{int(vat_rate)}%" if vat_rate.is_integer() else f"{vat_rate}%"

    summary_rows = [
        [Paragraph("Subtotal:", style_total_label), Paragraph(format_naira(invoice.subtotal), style_total_val)],
        [Paragraph(f"VAT ({vat_label_str}):", style_total_label), Paragraph(format_naira(vat_amount), style_total_val)],
    ]

    summary_table = Table(summary_rows, colWidths=[130, 120])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    due_banner_table = Table([[
        Paragraph("Total Due:", style_due_banner_label),
        Paragraph(format_naira(invoice.total_due), style_due_banner_val)
    ]], colWidths=[130, 120])
    due_banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PRIMARY_NAVY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))

    right_financial_flow = [
        summary_table,
        Spacer(1, 8),
        due_banner_table
    ]

    bottom_matrix = Table([[pay_table, right_financial_flow]], colWidths=[270, 270])
    bottom_matrix.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    story.append(KeepTogether([bottom_matrix]))

    # 5. TERMS, SIGNATURE & STAMP BLOCK
    terms_text = organization.terms if (organization and organization.terms) else (
        "Payment is expected within 30 days of the invoice date. Please forward your payment confirmation receipt directly to "
        "<b>info@arewanetventures.com</b> for immediate system deployment activation processing."
    )

    sig_elements = []
    stamp_elements = []

    if organization:
        if organization.stamp:
            try:
                stamp_path = organization.stamp.path
                if os.path.exists(stamp_path):
                    stamp_elements.append(Image(stamp_path, width=70, height=70))
            except Exception:
                pass

        if organization.signature:
            try:
                sig_path = organization.signature.path
                if os.path.exists(sig_path):
                    sig_elements.append(Image(sig_path, width=120, height=45))
                    sig_elements.append(Spacer(1, 2))
            except Exception:
                pass

    if not sig_elements:
        sig_elements.append(Spacer(1, 30))

    sig_elements.append(Paragraph("<b>Authorized Signature</b>", style_td_desc_sub))

    sig_stamp_table = Table([[
        stamp_elements if stamp_elements else [Paragraph("", style_td_desc_sub)],
        sig_elements
    ]], colWidths=[100, 150])
    sig_stamp_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    terms_matrix = Table([[
        [Paragraph("<b>Terms & Conditions:</b>", style_section_heading), Spacer(1, 4), Paragraph(terms_text, style_td_desc_sub)],
        sig_stamp_table
    ]], colWidths=[290, 250])
    terms_matrix.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    terms_flow = [
        HRFlowable(width="100%", thickness=0.5, color=BORDER_LIGHT, spaceBefore=15, spaceAfter=10),
        terms_matrix
    ]

    story.append(KeepTogether(terms_flow))

    doc.build(story, canvasmaker=NumberedCanvas)
