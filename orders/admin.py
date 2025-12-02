from django.contrib import admin
from .models import Order, OrderItem

# Inline for OrderItem inside Order
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = (
        "variant",
        "quantity",
        "unit_price",
        "discount_percent",
        "total_price",
        "total_after_discount",
        "created_at",
        "updated_at",
    )
    readonly_fields = (
        "unit_price",
        "total_price",
        "total_after_discount",
        "created_at",
        "updated_at",
    )
    show_change_link = True

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "status",
        "created_at",
        "updated_at",
        "total_amount_display",
        "total_after_discount_display",
    )
    list_filter = ("status", "created_at", "updated_at")
    search_fields = ("id", "user__username", "user__email")
    readonly_fields = (
        "total_amount_display",
        "total_after_discount_display",
        "created_at",
        "updated_at",
    )
    inlines = [OrderItemInline]
    ordering = ("-created_at",)

    def total_amount_display(self, obj):
        return obj.total_amount
    total_amount_display.short_description = "Total Amount"

    def total_after_discount_display(self, obj):
        return obj.total_after_discount
    total_after_discount_display.short_description = "Total After Discount"

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "variant_display",
        "quantity",
        "unit_price",
        "discount_percent",
        "total_price",
        "total_after_discount",
        "created_at",
        "updated_at",
    )
    list_filter = ("order__status", "created_at", "updated_at")
    search_fields = ("variant__product__name", "order__id")
    readonly_fields = (
        "unit_price",
        "total_price",
        "total_after_discount",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)

    def variant_display(self, obj):
        if obj.variant:
            return f"{obj.variant.product.name} ({obj.variant.color}, {obj.variant.size})"
        return "-"
    variant_display.short_description = "Product / Variant"
