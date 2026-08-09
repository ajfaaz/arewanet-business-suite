from django import template

register = template.Library()


@register.filter(name='money')
def money(value):
    if value is None or value == "":
        return "₦0.00"
    try:
        val = float(value)
        return f"₦{val:,.2f}"
    except (ValueError, TypeError):
        return "₦0.00"
