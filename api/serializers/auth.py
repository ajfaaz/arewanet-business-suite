from rest_framework import serializers
from django.contrib.auth import get_user_model
from invoices.models import Organization, UserProfile

User = get_user_model()


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "email", "phone", "address", "bank_name", "account_name", "account_number"]


class UserProfileSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "organization"]

    def get_organization(self, obj):
        if hasattr(obj, 'userprofile') and obj.userprofile and obj.userprofile.organization:
            return OrganizationSerializer(obj.userprofile.organization).data
        org = Organization.objects.first()
        if org:
            return OrganizationSerializer(org).data
        return None

    def get_role(self, obj):
        if hasattr(obj, 'userprofile') and obj.userprofile:
            return obj.userprofile.role
        return "ADMIN" if obj.is_superuser else "STAFF"
