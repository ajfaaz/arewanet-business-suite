from rest_framework import serializers


class DashboardSummarySerializer(serializers.Serializer):
    sales_today = serializers.DecimalField(max_digits=14, decimal_places=2)
    sales_this_month = serializers.DecimalField(max_digits=14, decimal_places=2)
    outstanding = serializers.DecimalField(max_digits=14, decimal_places=2)
    customers = serializers.IntegerField()
    products = serializers.IntegerField()
    quotations = serializers.IntegerField()
    invoices = serializers.IntegerField()
    payments = serializers.IntegerField()
    active_subscriptions = serializers.IntegerField()


class RevenueTrendSerializer(serializers.Serializer):
    month = serializers.CharField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)


class ReceivablesSerializer(serializers.Serializer):
    current = serializers.DecimalField(max_digits=14, decimal_places=2)
    days_30 = serializers.DecimalField(max_digits=14, decimal_places=2, source="30_days")
    days_60 = serializers.DecimalField(max_digits=14, decimal_places=2, source="60_days")
    days_90 = serializers.DecimalField(max_digits=14, decimal_places=2, source="90_days")


class TopCustomerSerializer(serializers.Serializer):
    name = serializers.CharField()
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2)


class TopProductSerializer(serializers.Serializer):
    product = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2)


class ActivityFeedSerializer(serializers.Serializer):
    type = serializers.CharField()
    message = serializers.CharField()
    time = serializers.CharField()


class NotificationSummarySerializer(serializers.Serializer):
    overdue_invoices = serializers.IntegerField()
    expiring_quotations = serializers.IntegerField()
    subscriptions_due = serializers.IntegerField()
