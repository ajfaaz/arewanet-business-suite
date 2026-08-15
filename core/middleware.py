from .context import get_organization_context


class OrganizationContextMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ctx = get_organization_context(request)
        request.org_context = ctx
        request.organization = ctx.organization
        request.membership = ctx.membership
        request.role = ctx.role

        response = self.get_response(request)
        return response
