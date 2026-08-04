from django.contrib import admin
from .models import (
    Organization, Customer, Invoice, InvoiceItem, 
    Quotation, Receipt, UserProfile, ActivityLog
)

# --- 1. Inline Tabular Frameworks ---
class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    readonly_fields = ('total',) # System handles totals automatically inside your save() model method

# --- 2. Advanced Custom Model Admin Classes ---
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'invoice_prefix', 'currency', 'created_at')
    search_fields = ('name', 'email', 'invoice_prefix')
    prepopulated_fields = {'slug': ('name',)} # Automatically populates slug from name while typing!

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'role')
    list_filter = ('role', 'organization')
    search_fields = ('user__username', 'user__email')

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'organization', 'phone', 'email')
    list_filter = ('organization',)
    search_fields = ('company_name', 'email')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_no', 'organization', 'customer', 'invoice_date', 'total_due', 'status')
    list_filter = ('status', 'organization', 'invoice_date')
    search_fields = ('invoice_no', 'customer__company_name', 'project_name')
    inlines = [InvoiceItemInline]

# --- 3. Simplified Direct Base Registrations ---
admin.site.register(ActivityLog)
admin.site.register(Quotation)
admin.site.register(Receipt)
