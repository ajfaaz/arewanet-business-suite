from django import forms
from .models import Invoice, InvoiceItem, Customer, Payment, ProductCategory, Product
from django.forms import inlineformset_factory

class InvoiceForm(forms.ModelForm):

    class Meta:
        model = Invoice
        fields = [
            'customer',
            'invoice_date',
            'due_date',
            'project_name',
            'deployment_phase',
            'status',
            'vat'
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'invoice_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'project_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. University Inventory Management System'}),
            'deployment_phase': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Option 3 (Enterprise Framework)'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'vat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00', 'id': 'id_vat'}),
        }
        labels = {
            'vat': 'VAT Rate (%)',
        }

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)

        if organization:
            self.fields['customer'].queryset = Customer.objects.filter(organization=organization)
            if organization.default_vat is not None and not self.instance.pk:
                self.fields['vat'].initial = organization.default_vat
        else:
            self.fields['customer'].queryset = Customer.objects.all()

        self.fields['customer'].empty_label = "Select Customer"


class CustomerForm(forms.ModelForm):

    class Meta:
        model = Customer
        fields = [
            'company_name',
            'contact_person',
            'email',
            'phone',
            'address'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company or Institution name'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact person title/name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full billing address'}),
        }


class InvoiceItemForm(forms.ModelForm):

    class Meta:
        model = InvoiceItem
        fields = [
            "product",
            "description",
            "qty",
            "unit_price",
        ]
        widgets = {
            "product": forms.Select(
                attrs={
                    "class": "form-select product-select"
                }
            ),
            "description": forms.TextInput(
                attrs={
                    "class": "form-control description"
                }
            ),
            "qty": forms.NumberInput(
                attrs={
                    "class": "form-control qty"
                }
            ),
            "unit_price": forms.NumberInput(
                attrs={
                    "class": "form-control unit-price"
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["product"].queryset = Product.objects.filter(
                organization=organization,
                active=True
            )
        self.fields["product"].empty_label = "-- Select Product --"


InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=1,
    can_delete=True,
)


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            'amount',
            'payment_method',
            'payment_date',
            'reference',
            'notes'
        ]
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. TRF-982341'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional payment notes'}),
        }


class ProductCategoryForm(forms.ModelForm):

    class Meta:
        model = ProductCategory
        fields = [
            "name",
            "description",
            "active",
        ]

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        category = super().save(commit=False)
        category.organization = self.organization
        if commit:
            category.save()
        return category


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product

        fields = [
            "category",
            "product_type",
            "name",
            "sku",
            "barcode",
            "description",
            "unit",
            "selling_price",
            "cost_price",
            "minimum_price",
            "notes",
            "taxable",
            "active",
            "image",
        ]

        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "product_type": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "sku": forms.TextInput(attrs={"class": "form-control"}),
            "barcode": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "unit": forms.TextInput(attrs={"class": "form-control"}),
            "selling_price": forms.NumberInput(attrs={"class": "form-control"}),
            "cost_price": forms.NumberInput(attrs={"class": "form-control"}),
            "minimum_price": forms.NumberInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "taxable": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)

        if self.organization:
            self.fields["category"].queryset = ProductCategory.objects.filter(
                organization=self.organization,
                active=True
            )

    def save(self, commit=True):
        product = super().save(commit=False)
        product.organization = self.organization

        if commit:
            product.save()

        return product
