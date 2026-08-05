import uuid
from datetime import datetime
from django.utils.text import slugify

def generate_invoice_number(prefix="INV"):
    year = datetime.now().year
    short_uuid = str(uuid.uuid4().int)[:4]
    return f"{prefix}-{year}-{short_uuid}"

def generate_reference(prefix="TRX"):
    short_uuid = str(uuid.uuid4().hex)[:8].upper()
    return f"{prefix}-{short_uuid}"

def format_phone(phone):
    if not phone:
        return ""
    digits = "".join(filter(str.isdigit, str(phone)))
    if len(digits) == 11 and digits.startswith("0"):
        return f"+234 {digits[1:4]} {digits[4:7]} {digits[7:]}"
    return phone

def format_currency(amount, currency="NGN"):
    try:
        val = float(amount or 0)
        symbol = "₦" if currency == "NGN" else f"{currency} "
        return f"{symbol}{val:,.2f}"
    except (ValueError, TypeError):
        return f"₦0.00"

def slugify_name(name):
    return slugify(name)
