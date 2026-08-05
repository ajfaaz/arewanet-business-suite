from django.dispatch import Signal

# Domain-level Custom Signals
invoice_created = Signal()
payment_recorded = Signal()
customer_registered = Signal()
