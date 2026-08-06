from rest_framework import serializers
from invoices.models import Product, ProductCategory


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["id", "name", "description", "active"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source="category.name")

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category",
            "category_name",
            "product_type",
            "sku",
            "unit",
            "selling_price",
            "cost_price",
            "description",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
