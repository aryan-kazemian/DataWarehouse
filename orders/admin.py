from django.contrib import admin
from .models import Order, OrderItem, OrderItemVariantInvoiceQuantity

@admin.register(OrderItemVariantInvoiceQuantity)
class OrderItemVariantInvoiceQuantityAdmin(admin.ModelAdmin):
    list_display = ("order_item", "variant_invoice_quantity", "deducted_quantity")
    autocomplete_fields = ("order_item", "variant_invoice_quantity")

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("unit_price", "total_price", "total_after_discount", "created_at", "updated_at")
    fields = ("variant", "quantity", "unit_price", "discount_percent", "total_price", "total_after_discount", "created_at", "updated_at")
    show_change_link = True
    autocomplete_fields = ("variant",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("variant", "variant__product")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user_display", "status", "created_at", "updated_at", "total_amount_display", "total_after_discount_display")
    list_filter = ("status", "created_at", "updated_at")
    search_fields = ("id", "user__username", "user__email")
    readonly_fields = ("total_amount_display", "total_after_discount_display", "created_at", "updated_at")
    inlines = [OrderItemInline]
    ordering = ("-created_at",)
    autocomplete_fields = ("user",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("user").prefetch_related("items__variant__product")

    def save_model(self, request, obj, form, change):
        obj.skip_analytics = True
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
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

    def user_display(self, obj):
        return obj.user.username if obj.user else "-"
    user_display.admin_order_field = "user"
    user_display.short_description = "User"

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order_display", "variant_display", "quantity", "unit_price", "discount_percent", "total_price", "total_after_discount", "created_at", "updated_at")
    list_filter = ("order__status", "created_at", "updated_at")
    search_fields = ("variant__product__name", "order__id")
    readonly_fields = ("unit_price", "total_price", "total_after_discount", "created_at", "updated_at")
    ordering = ("-created_at",)
    autocomplete_fields = ("variant", "order")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("order", "order__user", "variant", "variant__product")

    def save_model(self, request, obj, form, change):
        obj.order.skip_analytics = True
        super().save_model(request, obj, form, change)

    def variant_display(self, obj):
        if obj.variant:
            return f"{obj.variant.product.name} ({obj.variant.color}, {obj.variant.size})"
        return "-"
    variant_display.short_description = "Product / Variant"

    def order_display(self, obj):
        return f"#{obj.order.id}" if obj.order else "-"
    order_display.admin_order_field = "order"
    order_display.short_description = "Order"
