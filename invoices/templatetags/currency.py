from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def naira(value):
    if value is None or value == "":
        val = 0.0
    else:
        try:
            val = float(value)
        except (ValueError, TypeError):
            val = 0.0
    return f"₦{val:,.2f}"