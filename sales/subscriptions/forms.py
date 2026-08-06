from django import forms
from django.forms import inlineformset_factory
from sales.subscriptions.models import (
    Subscription,
    SubscriptionItem,
    SubscriptionTemplate,
    SubscriptionTemplateItem
)
from invoices.models import Customer, Product


class SubscriptionForm(forms.ModelForm):

    class Meta:
        model = Subscription
        fields = [
            "title",
            "customer",
            "template",
            "start_date",
            "billing_cycle",
            "auto_generate",
            "notes",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Monthly ICT & Web Hosting Support"}),
            "customer": forms.Select(attrs={"class": "form-select"}),
            "template": forms.Select(attrs={"class": "form-select", "id": "id_subscription_template"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "billing_cycle": forms.Select(attrs={"class": "form-select"}),
            "auto_generate": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Subscription notes or terms..."}),
        }

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["customer"].queryset = Customer.objects.filter(organization=organization).order_by("company_name")
            self.fields["template"].queryset = SubscriptionTemplate.objects.filter(organization=organization, is_active=True).order_by("title")
            self.fields["template"].required = False


class SubscriptionTemplateForm(forms.ModelForm):

    class Meta:
        model = SubscriptionTemplate
        fields = [
            "title",
            "billing_cycle",
            "description",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Hosting Basic Package"}),
            "billing_cycle": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Template package features & scope..."}),
        }


class SubscriptionItemForm(forms.ModelForm):

    class Meta:
        model = SubscriptionItem
        fields = ["product", "description", "qty", "unit_price", "discount"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select product-select"}),
            "description": forms.TextInput(attrs={"class": "form-control", "placeholder": "Service / Item description"}),
            "qty": forms.NumberInput(attrs={"class": "form-control item-qty", "step": "0.01"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control item-price", "step": "0.01"}),
            "discount": forms.NumberInput(attrs={"class": "form-control item-discount", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["product"].queryset = Product.objects.filter(organization=organization).order_by("name")


SubscriptionItemFormSet = inlineformset_factory(
    Subscription,
    SubscriptionItem,
    form=SubscriptionItemForm,
    extra=1,
    can_delete=True
)
