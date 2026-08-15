from invoices.models import Organization, OrganizationMembership


class OrganizationContext:

    def __init__(self, organization=None, membership=None):
        self.organization = organization
        self.membership = membership

    @property
    def role(self):
        if not self.membership:
            return None
        return self.membership.role

    def has_permission(self, permission_code):
        if not self.membership:
            return False
        return self.membership.has_permission(permission_code)

    def __str__(self):
        org_name = self.organization.name if self.organization else "No Organization"
        role_name = self.role.name if self.role else "No Role"
        return f"OrganizationContext({org_name} - {role_name})"


def get_organization_context(request):
    user = getattr(request, 'user', None)

    if not user or not user.is_authenticated:
        org = Organization.objects.first()
        if not org:
            org = Organization.objects.create(name='ArewaNet Ventures', slug='arewanet-ventures')
        return OrganizationContext(organization=org, membership=None)

    memberships = OrganizationMembership.objects.filter(
        user=user,
        is_active=True,
    ).select_related('organization', 'role')

    if not memberships.exists():
        org = getattr(getattr(user, 'userprofile', None), 'organization', None)
        if not org:
            org = Organization.objects.first()
            if not org:
                org = Organization.objects.create(name='ArewaNet Ventures', slug='arewanet-ventures')
        return OrganizationContext(organization=org, membership=None)

    # 1. Check if user set an active organization in session
    session_org_id = request.session.get('active_organization_id') if hasattr(request, 'session') else None
    if session_org_id:
        membership = memberships.filter(organization_id=session_org_id).first()
        if membership:
            return OrganizationContext(organization=membership.organization, membership=membership)

    # 2. Default to the user's first active membership
    first_membership = memberships.first()
    if hasattr(request, 'session'):
        request.session['active_organization_id'] = first_membership.organization.id

    return OrganizationContext(organization=first_membership.organization, membership=first_membership)
