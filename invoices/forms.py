from django import forms
from django.contrib.auth.models import User

from .models import (
    Invoice, InvoiceItem, Customer, Payment, ProductCategory, Product, Quotation, QuotationItem, QuotationTemplate,
    Organization, OrganizationMembership, Role, Permission
)
from core.choices import QuotationStatus
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


class QuotationForm(forms.ModelForm):
    vat = forms.DecimalField(required=False, initial=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    discount = forms.DecimalField(required=False, initial=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    valid_until = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    terms = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))

    class Meta:
        model = Quotation
        fields = [
            'customer',
            'template',
            'quotation_date',
            'valid_until',
            'status',
            'vat',
            'discount',
            'notes',
            'terms',
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'template': forms.Select(attrs={'class': 'form-select'}),
            'quotation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        if self.organization:
            self.fields['customer'].queryset = Customer.objects.filter(organization=self.organization)
            tpl_qs = QuotationTemplate.objects.filter(
                organization=self.organization,
                is_active=True
            )
            if self.instance.pk and self.instance.template_id:
                tpl_qs = QuotationTemplate.objects.filter(
                    organization=self.organization
                ).filter(
                    models.Q(is_active=True) | models.Q(pk=self.instance.template_id)
                )
            self.fields['template'].queryset = tpl_qs
            if not self.instance.pk:
                default_tpl = QuotationTemplate.objects.filter(
                    organization=self.organization,
                    is_default=True,
                    is_active=True
                ).first()
                if default_tpl:
                    self.fields['template'].initial = default_tpl.pk
        else:
            self.fields['customer'].queryset = Customer.objects.all()
            self.fields['template'].queryset = QuotationTemplate.objects.filter(is_active=True)

        self.fields['customer'].empty_label = "Select Customer"
        self.fields['template'].empty_label = "-- Select Quotation Template --"
        self.fields['template'].required = False

    def clean_template(self):
        template = self.cleaned_data.get('template')
        if template and self.organization:
            if template.organization_id != self.organization.id:
                raise forms.ValidationError("Invalid template selection for this organization.")
            is_bound_instance_tpl = bool(self.instance.pk and self.instance.template_id == template.id)
            if not template.is_active and not is_bound_instance_tpl:
                raise forms.ValidationError("The selected quotation template is inactive.")
        return template

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk and self.instance.status != "DRAFT" and self.instance.status != QuotationStatus.DRAFT:
            raise forms.ValidationError("Issued quotations cannot be edited.")
        return cleaned_data



class QuotationItemForm(forms.ModelForm):
    description = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control description'})
    )
    qty = forms.DecimalField(
        required=False,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control qty', 'step': '0.01'})
    )
    unit_price = forms.DecimalField(
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control unit-price', 'step': '0.01'})
    )
    discount = forms.DecimalField(
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control discount', 'step': '0.01'})
    )

    class Meta:
        model = QuotationItem
        fields = [
            'product',
            'description',
            'qty',
            'unit_price',
            'discount',
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select product-select'}),
        }

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['product'].queryset = Product.objects.filter(
                organization=organization,
                active=True
            )
        self.fields['product'].empty_label = "-- Select Product --"

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        description = cleaned_data.get('description')
        qty = cleaned_data.get('qty')
        unit_price = cleaned_data.get('unit_price')
        discount = cleaned_data.get('discount')

        if qty is None:
            cleaned_data['qty'] = 1
            self.cleaned_data['qty'] = 1

        if unit_price is None:
            price = product.selling_price if product else 0
            cleaned_data['unit_price'] = price
            self.cleaned_data['unit_price'] = price

        if discount is None:
            cleaned_data['discount'] = 0
            self.cleaned_data['discount'] = 0

        if not description:
            desc = product.name if product else "Quotation Item"
            cleaned_data['description'] = desc
            self.cleaned_data['description'] = desc

        return cleaned_data




QuotationItemFormSet = inlineformset_factory(
    Quotation,
    QuotationItem,
    form=QuotationItemForm,
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


class QuotationTemplateForm(forms.ModelForm):

    class Meta:
        model = QuotationTemplate
        fields = [
            "name",
            "description",
            "style",
            "is_active",
            "is_default",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Modern Corporate Template"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Optional description for this template"}),
            "style": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if name and self.organization:
            qs = QuotationTemplate.objects.filter(
                organization=self.organization,
                name__iexact=name
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("A template with this name already exists in your organization.")
        return name

    def clean(self):
        cleaned_data = super().clean()
        is_active = cleaned_data.get("is_active")
        is_default = cleaned_data.get("is_default")

        if is_default and not is_active:
            raise forms.ValidationError("A default template must be set to Active.")

        if self.instance and self.instance.pk and self.instance.is_default and not is_active:
            raise forms.ValidationError("Cannot deactivate the current default template until another active template is set as default.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.organization:
            instance.organization = self.organization
        if commit:
            instance.save()
        return instance


class OrganizationSettingsForm(forms.ModelForm):

    CURRENCY_CHOICES = [
        ('NGN', 'NGN (₦) - Nigerian Naira'),
        ('USD', 'USD ($) - US Dollar'),
        ('EUR', 'EUR (€) - Euro'),
        ('GBP', 'GBP (£) - British Pound'),
        ('CAD', 'CAD (CA$) - Canadian Dollar'),
        ('AUD', 'AUD (A$) - Australian Dollar'),
    ]

    currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Organization
        fields = [
            'name',
            'logo',
            'signature',
            'stamp',
            'phone',
            'email',
            'website',
            'address',
            'currency',
            'invoice_prefix',
            'default_vat',
            'bank_name',
            'account_name',
            'account_number',
            'terms',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Organization Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+234 800 000 0000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'info@organization.com'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.organization.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Physical / Billing Address'}),
            'invoice_prefix': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. ANV'}),
            'default_vat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '7.50'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. First Bank of Nigeria'}),
            'account_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Account Holder Name'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit account number'}),
            'terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Standard quotation & invoice terms'}),
        }


class MemberInviteForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username (e.g. jdoe)'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'member@organization.com'})
    )
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank for default password'}),
        help_text='If left blank, a secure default password will be assigned.'
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='-- Select Role --'
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username


class MemberEditForm(forms.ModelForm):
    role = forms.ModelChoiceField(
        queryset=Role.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = OrganizationMembership
        fields = ['role', 'is_active']
        widgets = {
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class RoleForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False
    )

    class Meta:
        model = Role
        fields = ['name', 'description', 'permissions']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Role Name (e.g. Senior Billing Officer)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe responsibilities'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            from django.utils.text import slugify
            slug = slugify(name)
            qs = Role.objects.filter(slug=slug)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("A role with this name already exists.")
        return name


