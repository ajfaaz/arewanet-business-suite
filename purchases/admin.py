from django.contrib import admin
from purchases.models import Supplier, PurchaseOrder, PurchaseOrderItem


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("code", "company_name", "contact_person", "email", "phone", "organization", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("code", "company_name", "contact_person", "email", "phone")


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "organization", "supplier", "warehouse", "order_date", "status", "total")
    list_filter = ("organization", "status", "order_date")
    search_fields = ("order_number", "supplier__company_name")
    inlines = [PurchaseOrderItemInline]
