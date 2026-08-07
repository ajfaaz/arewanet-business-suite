from rest_framework.viewsets import ModelViewSet
from invoices.views import _get_user_organization


class OrganizationModelViewSet(ModelViewSet):
    """
    Base ViewSet enforcing organization-level multi-tenant isolation.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        org = _get_user_organization(self.request.user)
        if org and hasattr(queryset.model, "organization"):
            return queryset.filter(organization=org)
        return queryset

    def perform_create(self, serializer):
        org = _get_user_organization(self.request.user)
        if org and hasattr(serializer.Meta.model, "organization"):
            serializer.save(organization=org)
        else:
            serializer.save()
