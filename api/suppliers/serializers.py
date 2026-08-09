from rest_framework import serializers
from purchases.models import Supplier


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            "id",
            "code",
            "company_name",
            "contact_person",
            "email",
            "phone",
            "address",
            "tax_number",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["code", "created_at", "updated_at"]
