from decimal import Decimal
from datetime import datetime, date
from django.db.models import Q
from invoices.models import Invoice, Payment as LegacyPayment
from sales.payments.models import Payment as EnterprisePayment
from sales.models import CreditNote, DebitNote


class StatementService:

    @classmethod
    def generate_statement(cls, customer, start_date=None, end_date=None):
        """
        Generate chronological customer ledger statement with running balance.
        """
        org = customer.organization

        # Parse string dates if passed
        if isinstance(start_date, str) and start_date.strip():
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        elif not isinstance(start_date, date):
            start_date = None

        if isinstance(end_date, str) and end_date.strip():
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        elif not isinstance(end_date, date):
            end_date = None

        raw_events = []

        # 1. Invoices
        invoices = Invoice.objects.filter(customer=customer).exclude(status='CANCELLED')
        for inv in invoices:
            dt = inv.invoice_date
            raw_events.append({
                'date': dt,
                'type': 'INVOICE',
                'reference': inv.invoice_no,
                'description': f"Invoice #{inv.invoice_no} ({inv.project_name or 'Sales Invoice'})",
                'debit': Decimal(str(inv.total_due or 0)),
                'credit': Decimal('0.00'),
                'instance': inv,
            })

        # 2. Enterprise Payments
        payments = EnterprisePayment.objects.filter(customer=customer).exclude(status__in=['REVERSED', 'REFUNDED', 'FAILED'])
        for p in payments:
            dt = p.payment_date
            ref = p.receipt_number or p.reference or 'Payment'
            raw_events.append({
                'date': dt,
                'type': 'PAYMENT',
                'reference': ref,
                'description': f"Payment Received ({p.get_payment_method_display()})",
                'debit': Decimal('0.00'),
                'credit': Decimal(str(p.amount or 0)),
                'instance': p,
            })

        # 3. Legacy Payments
        legacy_payments = LegacyPayment.objects.filter(invoice__customer=customer)
        for lp in legacy_payments:
            dt = lp.payment_date
            ref = lp.reference or f"RCP-{lp.pk:04d}"
            raw_events.append({
                'date': dt,
                'type': 'PAYMENT',
                'reference': ref,
                'description': f"Legacy Payment ({lp.payment_method})",
                'debit': Decimal('0.00'),
                'credit': Decimal(str(lp.amount or 0)),
                'instance': lp,
            })

        # 4. Credit Notes
        credit_notes = CreditNote.objects.filter(customer=customer).exclude(status='CANCELLED')
        for cn in credit_notes:
            dt = cn.created_at.date() if hasattr(cn.created_at, 'date') else cn.created_at
            raw_events.append({
                'date': dt,
                'type': 'CREDIT_NOTE',
                'reference': cn.credit_note_no,
                'description': f"Credit Note #{cn.credit_note_no} ({cn.reason})",
                'debit': Decimal('0.00'),
                'credit': Decimal(str(cn.amount or 0)),
                'instance': cn,
            })

        # 5. Debit Notes
        debit_notes = DebitNote.objects.filter(customer=customer).exclude(status='CANCELLED')
        for dn in debit_notes:
            dt = dn.created_at.date() if hasattr(dn.created_at, 'date') else dn.created_at
            raw_events.append({
                'date': dt,
                'type': 'DEBIT_NOTE',
                'reference': dn.debit_note_no,
                'description': f"Debit Note #{dn.debit_note_no} ({dn.reason})",
                'debit': Decimal(str(dn.amount or 0)),
                'credit': Decimal('0.00'),
                'instance': dn,
            })

        # Sort all events chronologically
        raw_events.sort(key=lambda x: (x['date'], x['reference']))

        opening_balance = Decimal('0.00')
        statement_transactions = []
        running_balance = Decimal('0.00')
        total_debits = Decimal('0.00')
        total_credits = Decimal('0.00')

        for ev in raw_events:
            ev_date = ev['date']

            # If event occurred before start_date, accumulate opening_balance
            if start_date and ev_date < start_date:
                opening_balance += (ev['debit'] - ev['credit'])
                continue

            # If event occurred after end_date, ignore for this period
            if end_date and ev_date > end_date:
                continue

            if not statement_transactions:
                running_balance = opening_balance

            running_balance += (ev['debit'] - ev['credit'])
            total_debits += ev['debit']
            total_credits += ev['credit']

            ev_copy = dict(ev)
            ev_copy['running_balance'] = running_balance
            statement_transactions.append(ev_copy)

        closing_balance = running_balance if statement_transactions else opening_balance

        return {
            'customer': customer,
            'organization': org,
            'start_date': start_date,
            'end_date': end_date,
            'opening_balance': opening_balance,
            'closing_balance': closing_balance,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'transactions': statement_transactions,
            'generated_at': date.today(),
        }
