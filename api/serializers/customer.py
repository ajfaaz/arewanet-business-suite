from rest_framework import serializers
from invoices.models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "company_name",
            "contact_person",
            "email",
            "phone",
            "address",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CustomerSummarySerializer(serializers.Serializer):
    customer = serializers.CharField()
    outstanding = serializers.DecimalField(max_digits=12, decimal_places=2)
    paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    quotations = serializers.IntegerField()
    invoices = serializers.IntegerField()
    payments = serializers.IntegerField()
