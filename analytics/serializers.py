from rest_framework import serializers
from .models import FactAnalytics

class FactSalesVariantSerializer(serializers.Serializer):
    def to_representation(self, variant):
        fact = self.context.get('fact')

        product = getattr(variant, 'product', None)

        return {
            # DimDate fields
            "jalali_date": fact.date.jalali_date if fact else None,
            "day_of_week": fact.date.day_of_week if fact else None, 
            "month_name": fact.date.month_name if fact else None,
            "quarter": fact.date.quarter if fact else None,
            "is_holiday": fact.date.is_holiday if fact else None,

            # DimUser fields
            "username": fact.user.username if fact else None,
            "gender": fact.user.gender if fact else None,
            "city": fact.user.city if fact else None,
            "registration_date": fact.user.registration_date if fact else None,
            "age_range": fact.user.age_range if fact else None,

            # DimVariantOrder fields
            "color": variant.color,
            "size": variant.size,
            "quantity": variant.quantity,
            "unit_price": variant.unit_price,
            "discount_percent": variant.discount_percent,
            "total_price": variant.total_price,
            "total_after_discount": variant.total_after_discount,

            # DimProductBase fields
            "product_id": product.product_id if product else None,
            "product_name": product.name if product else None,
            "rating": product.rating if product else None,
            "expire_date": product.expire_date if product else None,
            "is_available": product.is_available if product else None,
            "is_exciting": product.is_exciting if product else None,
            "free_shipping": product.free_shipping if product else None,
            "has_gift": product.has_gift if product else None,
            "is_budget_friendly": product.is_budget_friendly if product else None,
            "price": product.price if product else None,
            "brand": product.brand if product else None,
            "category_level_1": product.category_level_1 if product else None,
            "category_level_2": product.category_level_2 if product else None,
            "category_level_3": product.category_level_3 if product else None,
        }

class FactAnalyticsSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()

    class Meta:
        model = FactAnalytics
        fields = [
            "date",
            "total_order_quantity",
            "initial_order_quantity",
            "process_order_quantity",
            "sent_order_quantity",
            "done_order_quantity",
            "cancel_order_quantity",
            "rejected_order_quantity",
        ]

    def get_date(self, obj):
        d = obj.date
        return {
            "jalali_date": d.jalali_date,
            "day_of_week": d.day_of_week,
            "month_name": d.month_name,
            "quarter": d.quarter,
            "is_holiday": d.is_holiday,
        }

class TopUserSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(allow_null=True)
    username = serializers.CharField(allow_null=True)
    gender = serializers.CharField(allow_null=True)
    city = serializers.CharField(allow_null=True)
    registration_date = serializers.DateField(allow_null=True)
    age_range = serializers.CharField(allow_null=True)
    total_orders = serializers.IntegerField()
    total_spent = serializers.IntegerField()

class PerDateSerializer(serializers.Serializer):
    date = serializers.DateField()
    quantity = serializers.IntegerField()
    users = serializers.IntegerField()

class MostSoldProductSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    product_id = serializers.IntegerField(allow_null=True)
    product_name = serializers.CharField(allow_null=True)
    brand = serializers.CharField(allow_null=True)
    supplier = serializers.CharField(allow_null=True)
    category_level_1 = serializers.CharField(allow_null=True)
    category_level_2 = serializers.CharField(allow_null=True)
    category_level_3 = serializers.CharField(allow_null=True)
    rating = serializers.IntegerField(allow_null=True)
    price = serializers.IntegerField(allow_null=True)
    expire_date = serializers.DateField(allow_null=True)
    is_available = serializers.BooleanField(allow_null=True)
    is_exciting = serializers.BooleanField(allow_null=True)
    free_shipping = serializers.BooleanField(allow_null=True)
    has_gift = serializers.BooleanField(allow_null=True)
    is_budget_friendly = serializers.BooleanField(allow_null=True)
    total_quantity_sold = serializers.IntegerField()
    total_sold_price = serializers.IntegerField()
    user_quantity = serializers.IntegerField()
    per_date = PerDateSerializer(many=True)

class TopSupplierSerializer(serializers.Serializer):
    supplier = serializers.CharField(allow_null=True)
    total_quantity_sold = serializers.IntegerField()
    total_sold_price = serializers.IntegerField()
    user_quantity = serializers.IntegerField()