from django.contrib import admin
from .models import Order, OrderItem


# --------------------------------------
# Inline for OrderItem (optimized)
# --------------------------------------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    per_page = 20  # prevent loading hundreds of rows at once
    readonly_fields = (
        "unit_price",
        "total_price",
        "total_after_discount",
        "created_at",
        "updated_at",
    )
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
    show_change_link = True


# --------------------------------------
# Order Admin
# --------------------------------------
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

    # 🔥🔥 CRITICAL FIX:
    # Disable analytics syncing when saving from admin
    def save_model(self, request, obj, form, change):
        obj.skip_analytics = True  # This flag stops analytics logic in Order.save()
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        # Disable analytics sync on inline OrderItem saves
        instances = formset.save(commit=False)
        for inst in instances:
            inst.order.skip_analytics = True
            inst.save()
        formset.save_m2m()

    def total_amount_display(self, obj):
        return obj.total_amount
    total_amount_display.short_description = "Total Amount"

    def total_after_discount_display(self, obj):
        return obj.total_after_discount
    total_after_discount_display.short_description = "Total After Discount"


# --------------------------------------
# OrderItem Admin
# --------------------------------------
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

    def save_model(self, request, obj, form, change):
        obj.order.skip_analytics = True  # disable analytics sync
        super().save_model(request, obj, form, change)

    def variant_display(self, obj):
        if obj.variant:
            return f"{obj.variant.product.name} ({obj.variant.color}, {obj.variant.size})"
        return "-"
    variant_display.short_description = "Product / Variant"
