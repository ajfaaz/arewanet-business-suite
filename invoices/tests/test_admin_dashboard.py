from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from invoices.models import Organization, OrganizationMembership, Role, Permission, UserProfile, ActivityLog
from invoices.forms import OrganizationSettingsForm, MemberInviteForm, MemberEditForm, RoleForm


class AdminDashboardTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='superadmin', password='password123', email='superadmin@example.com')
        self.client.login(username='superadmin', password='password123')

        self.org = Organization.objects.create(
            name="ArewaNet Enterprise Org",
            slug="arewanet-enterprise-org",
            currency="NGN",
            default_vat=Decimal("7.50"),
            phone="+234 800 111 2222",
            email="info@arewanet.example.com",
            address="Plot 123 Central Business District, Abuja"
        )
        UserProfile.objects.create(user=self.user, organization=self.org, role='ADMIN')

        # Retrieve or create permissions safely
        self.perm_view, _ = Permission.objects.get_or_create(code="organization.view", defaults={"name": "View Org", "module": "organization", "action": "view"})
        self.perm_edit, _ = Permission.objects.get_or_create(code="organization.edit", defaults={"name": "Edit Org", "module": "organization", "action": "edit"})
        self.perm_user_create, _ = Permission.objects.get_or_create(code="user.create", defaults={"name": "Create User", "module": "user", "action": "create"})
        self.perm_user_edit, _ = Permission.objects.get_or_create(code="user.edit", defaults={"name": "Edit User", "module": "user", "action": "edit"})
        self.perm_user_disable, _ = Permission.objects.get_or_create(code="user.disable", defaults={"name": "Disable User", "module": "user", "action": "disable"})
        self.perm_role_create, _ = Permission.objects.get_or_create(code="role.create", defaults={"name": "Create Role", "module": "role", "action": "create"})
        self.perm_role_edit, _ = Permission.objects.get_or_create(code="role.edit", defaults={"name": "Edit Role", "module": "role", "action": "edit"})

        self.admin_role, _ = Role.objects.get_or_create(slug="administrator", defaults={"name": "Administrator", "is_system_role": True})
        self.admin_role.permissions.add(self.perm_view, self.perm_edit, self.perm_user_create, self.perm_user_edit, self.perm_user_disable, self.perm_role_create, self.perm_role_edit)

        self.membership = OrganizationMembership.objects.create(
            organization=self.org,
            user=self.user,
            role=self.admin_role,
            is_active=True
        )

    def test_admin_settings_dashboard_get(self):
        url = reverse('admin_settings_dashboard')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Settings & Administration")
        self.assertContains(res, "ArewaNet Enterprise Org")


    def test_admin_settings_tabs_get(self):
        tabs = ['overview', 'organization', 'members', 'roles', 'templates', 'activity']
        for tab in tabs:
            url = reverse('admin_settings_dashboard') + f"?tab={tab}"
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200)

    def test_organization_settings_update_post(self):
        url = reverse('organization_settings_update')
        data = {
            'name': 'Updated ArewaNet Corp',
            'phone': '+234 809 999 8888',
            'email': 'contact@arewanet.corp',
            'website': 'https://arewanet.corp',
            'address': 'Updated Tech Avenue, Kano',
            'currency': 'USD',
            'invoice_prefix': 'ANVC',
            'default_vat': '10.00',
            'bank_name': 'Zenith Bank',
            'account_name': 'ArewaNet Corp',
            'account_number': '1234567890',
            'terms': 'Updated payment terms: 30 days.'
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, 302)
        self.org.refresh_from_db()
        self.assertEqual(self.org.name, 'Updated ArewaNet Corp')
        self.assertEqual(self.org.currency, 'USD')
        self.assertEqual(self.org.default_vat, Decimal('10.00'))

    def test_member_create_post(self):
        url = reverse('member_create')
        data = {
            'username': 'newstaff',
            'email': 'newstaff@example.com',
            'first_name': 'New',
            'last_name': 'Staff',
            'password': 'Password123!',
            'role': self.admin_role.pk
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, 302)
        new_user = User.objects.filter(username='newstaff').first()
        self.assertIsNotNone(new_user)
        m = OrganizationMembership.objects.filter(organization=self.org, user=new_user).first()
        self.assertIsNotNone(m)
        self.assertEqual(m.role, self.admin_role)

    def test_member_toggle_active_post(self):
        staff_user = User.objects.create_user(username='staffmember', password='password123')
        staff_m = OrganizationMembership.objects.create(
            organization=self.org,
            user=staff_user,
            role=self.admin_role,
            is_active=True
        )
        url = reverse('member_toggle_active', kwargs={'pk': staff_m.pk})
        res = self.client.post(url)
        self.assertEqual(res.status_code, 302)
        staff_m.refresh_from_db()
        self.assertFalse(staff_m.is_active)

    def test_role_create_post(self):
        url = reverse('role_create')
        data = {
            'name': 'Senior Financial Manager',
            'description': 'Manages all corporate financial records and invoices',
            'permissions': [self.perm_view.pk, self.perm_edit.pk]
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, 302)
        r = Role.objects.filter(name='Senior Financial Manager').first()
        self.assertIsNotNone(r)
        self.assertEqual(r.permissions.count(), 2)

    def test_navigation_sidebar_and_topbar(self):
        res = self.client.get(reverse('dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, reverse('admin_settings_dashboard'))
