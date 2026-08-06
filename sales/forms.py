from django import forms
from sales.models import Invoice, Quotation, BaseDocument


class BaseDocumentForm(forms.ModelForm):

    class Meta:
        model = None
        fields = [
            "customer",
            "document_number",
            "issue_date",
            "due_date",
            "status",
            "notes",
        ]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-select"}),
            "document_number": forms.TextInput(attrs={"class": "form-control"}),
            "issue_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        doc = super().save(commit=False)
        if self.organization:
            doc.organization = self.organization
        if commit:
            doc.save()
        return doc


class InvoiceForm(BaseDocumentForm):

    class Meta(BaseDocumentForm.Meta):
        model = Invoice
        fields = BaseDocumentForm.Meta.fields + [
            "payment_reference",
            "vat",
        ]
        widgets = {
            **BaseDocumentForm.Meta.widgets,
            "payment_reference": forms.TextInput(attrs={"class": "form-control"}),
            "vat": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }


class QuotationForm(BaseDocumentForm):

    class Meta(BaseDocumentForm.Meta):
        model = Quotation
        fields = BaseDocumentForm.Meta.fields + [
            "expiry_date",
            "accepted",
        ]
        widgets = {
            **BaseDocumentForm.Meta.widgets,
            "expiry_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "accepted": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CreditNoteForm(forms.Form):
    invoice = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_credit_invoice"}),
        label="Invoice"
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "0.00", "step": "0.01"}),
        label="Credit Amount (₦)"
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Reason for issuing credit note..."}),
        label="Reason"
    )

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)
        from invoices.models import Invoice
        if organization:
            self.fields["invoice"].queryset = Invoice.objects.filter(organization=organization).exclude(status__in=["PAID", "CANCELLED"]).select_related("customer")


class DebitNoteForm(forms.Form):
    invoice = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_debit_invoice"}),
        label="Invoice"
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "0.00", "step": "0.01"}),
        label="Debit Amount (₦)"
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Reason for issuing debit note..."}),
        label="Reason"
    )

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)
        from invoices.models import Invoice
        if organization:
            self.fields["invoice"].queryset = Invoice.objects.filter(organization=organization).exclude(status="CANCELLED").select_related("customer")

