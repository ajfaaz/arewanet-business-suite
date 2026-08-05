from invoices.models import Customer, Invoice
from invoices.services.audit_service import AuditService

class CustomerService:

    @staticmethod
    def create_customer(organization, customer_data, user=None):
        """
        Create a new customer under the given organization.
        """
        customer = Customer.objects.create(
            organization=organization,
            company_name=customer_data.get('company_name'),
            contact_person=customer_data.get('contact_person', ''),
            email=customer_data.get('email', ''),
            phone=customer_data.get('phone', ''),
            address=customer_data.get('address', '')
        )

        if user:
            AuditService.log(
                user=user,
                action=f"Created Customer {customer.company_name}",
                reference=customer.company_name
            )

        return customer

    @staticmethod
    def get_customer_history(customer):
        """
        Retrieve all invoices and financial history for a customer.
        """
        invoices = Invoice.objects.filter(customer=customer).order_by('-invoice_date')
        total_spent = sum(inv.total_due for inv in invoices if inv.status in ['PAID', 'Paid'])
        balance_due = sum(inv.balance for inv in invoices if hasattr(inv, 'balance'))
        return {
            'invoices': invoices,
            'total_spent': total_spent,
            'balance_due': balance_due
        }
