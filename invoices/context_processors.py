from core.context import get_organization_context
from invoices.models import OrganizationMembership
from invoices.navigation import get_user_menu


def active_organization_context(request):
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {}

    ctx = getattr(request, 'org_context', None)
    if not ctx:
        ctx = get_organization_context(request)

    memberships = OrganizationMembership.objects.filter(
        user=request.user,
        is_active=True,
    ).select_related('organization', 'role')

    resolver_match = getattr(request, 'resolver_match', None)
    current_url_name = resolver_match.url_name if resolver_match else ''

    user_menu_sections = get_user_menu(
        membership=ctx.membership,
        current_url_name=current_url_name,
        is_superuser=request.user.is_superuser
    )

    return {
        'organization': ctx.organization,
        'current_organization': ctx.organization,
        'active_organization': ctx.organization,
        'membership': ctx.membership,
        'current_membership': ctx.membership,
        'role': ctx.role,
        'current_role': ctx.role,
        'org_context': ctx,
        'user_memberships': memberships,
        'user_menu_sections': user_menu_sections,
    }
