from datetime import date
from django import forms
from core.choices import PaymentMethod, PaymentStatus
from sales.payments.models import Payment
from invoices.models import Customer, Invoice


class PaymentForm(forms.ModelForm):

    class Meta:
        model = Payment
        fields = [
            'customer',
            'amount',
            'payment_method',
            'payment_date',
            'reference',
            'notes',
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. TRF-982341 / POS-7712'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes / teller info'}),
        }

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['customer'].queryset = Customer.objects.filter(organization=organization)
        self.fields['customer'].empty_label = "Select Customer"
        if 'payment_date' not in self.initial or not self.initial['payment_date']:
            self.fields['payment_date'].initial = date.today()


class MultiInvoicePaymentForm(forms.Form):

    customer = forms.ModelChoiceField(
        queryset=Customer.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_multi_customer'})
    )

    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'})
    )

    payment_method = forms.ChoiceField(
        choices=PaymentMethod.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    payment_date = forms.DateField(
        initial=date.today,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    reference = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. BULK-TRF-99234'})
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Multi-invoice allocation notes'})
    )

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['customer'].queryset = Customer.objects.filter(organization=organization)
