from django.contrib import admin
from .models import Supplier, PurchaseInvoice, PurchaseItem

class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1
    readonly_fields = ("total_price",)
    autocomplete_fields = ("product_variant",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("product_variant__product")

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)

@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "Supplier", "status", "total_price", "created_at", "delivery_date")
    list_filter = ("status", "Supplier", "created_at")
    search_fields = ("title", "Supplier__name")
    readonly_fields = ("created_at", "updated_at", "total_price")
    inlines = [PurchaseItemInline]
    autocomplete_fields = ("Supplier",)
    fieldsets = (
        ("اطلاعات اصلی", {"fields": ("title", "Supplier", "status")}),
        ("مبلغ و زمان", {"fields": ("total_price", ("delivery_date", "delivery_time"))}),
        ("زمان‌ها", {"fields": ("created_at", "updated_at")}),
    )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.update_total_price()

@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ("id", "invoice", "product_variant_name", "quantity", "total_price")
    list_filter = ("invoice",)
    autocomplete_fields = ("product_variant", "invoice")
    readonly_fields = ("total_price",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("product_variant__product", "invoice")

    def product_variant_name(self, obj):
        if obj.product_variant and obj.product_variant.product:
            return f"{obj.product_variant.product.name} - {obj.product_variant.sku}"
        return "-"
    product_variant_name.short_description = "Product Variant"
