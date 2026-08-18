from django import forms
from purchases.models import Supplier, PurchaseOrder
from inventory.models import Warehouse


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            "company_name",
            "contact_person",
            "email",
            "phone",
            "address",
            "tax_number",
            "is_active",
        ]
        widgets = {
            "company_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Acme Supplies Ltd"}),
            "contact_person": forms.TextInput(attrs={"class": "form-control", "placeholder": "Contact Person Name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "supplier@example.com"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "+234..."}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Office / Billing Address"}),
            "tax_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "TIN / Tax Reg No"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            "supplier",
            "warehouse",
            "order_date",
            "expected_date",
            "notes",
        ]
        widgets = {
            "supplier": forms.Select(attrs={"class": "form-select"}),
            "warehouse": forms.Select(attrs={"class": "form-select"}),
            "order_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "expected_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Order notes / delivery terms..."}),
        }

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["supplier"].queryset = Supplier.objects.filter(organization=organization, is_active=True)
            self.fields["warehouse"].queryset = Warehouse.objects.filter(organization=organization, is_active=True)
