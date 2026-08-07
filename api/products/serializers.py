from rest_framework import serializers
from invoices.models import Product, ProductCategory


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )
    price = serializers.DecimalField(
        source="selling_price",
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    is_active = serializers.BooleanField(
        source="active",
        read_only=True
    )

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "category",
            "category_name",
            "price",
            "selling_price",
            "product_type",
            "sku",
            "barcode",
            "is_active",
        )


class ProductDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )
    price = serializers.DecimalField(
        source="selling_price",
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    is_active = serializers.BooleanField(
        source="active",
        read_only=True
    )

    class Meta:
        model = Product
        fields = "__all__"


class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        exclude = ("organization",)
