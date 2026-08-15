from django.contrib import admin
from .models import (
    Organization, Customer, Invoice, InvoiceItem, 
    Quotation, Receipt, UserProfile, ActivityLog, OrganizationMembership, Role, Permission
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

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "module",
        "action",
        "is_active",
    )
    list_filter = (
        "module",
        "action",
        "is_active",
    )
    search_fields = (
        "code",
        "name",
    )

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "is_system_role",
        "is_active",
    )
    list_filter = (
        "is_system_role",
        "is_active",
    )
    search_fields = (
        "name",
        "slug",
    )
    filter_horizontal = ("permissions",)

@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "organization",
        "role",
        "is_active",
        "joined_at",
    )
    list_filter = (
        "organization",
        "role",
        "is_active",
    )
    search_fields = (
        "user__username",
        "user__email",
        "organization__name",
        "role__name",
    )

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
