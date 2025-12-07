from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin
from .models import Brand, Category, Product, Variant, VariantInvoiceQuantity
from suppliers.models import PurchaseInvoice

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    mptt_indent_field = "name"
    list_display = ("tree_actions", "indented_title", "slug")
    list_display_links = ("indented_title",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

class VariantInvoiceQuantityInline(admin.TabularInline):
    model = VariantInvoiceQuantity
    extra = 1
    autocomplete_fields = ("invoice",)
    fields = ("invoice", "quantity")
    readonly_fields = ()
    show_change_link = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("invoice")

class VariantInline(admin.TabularInline):
    model = Variant
    extra = 1
    fields = ("sku", "color", "size")
    show_change_link = True

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "brand_name", "category_name", "price", "rating", "is_available", "is_exciting", "free_shipping", "has_gift", "is_budget_friendly", "created_at", "updated_at")
    list_filter = ("brand", "category", "is_available", "is_exciting", "free_shipping", "has_gift", "is_budget_friendly")
    search_fields = ("name", "brand__name", "category__name")
    inlines = [VariantInline]
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("brand", "category")

    def brand_name(self, obj):
        return obj.brand.name if obj.brand else "-"
    brand_name.admin_order_field = "brand"
    brand_name.short_description = "Brand"

    def category_name(self, obj):
        return obj.category.name if obj.category else "-"
    category_name.admin_order_field = "category"
    category_name.short_description = "Category"

@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "product_name", "color", "size", "created_at", "updated_at")
    list_filter = ("product", "color", "size")
    search_fields = ("sku", "product__name", "color", "size")
    readonly_fields = ("created_at", "updated_at")
    inlines = [VariantInvoiceQuantityInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("product")

    def product_name(self, obj):
        return obj.product.name if obj.product else "-"
    product_name.admin_order_field = "product"
    product_name.short_description = "Product"

@admin.register(VariantInvoiceQuantity)
class VariantInvoiceQuantityAdmin(admin.ModelAdmin):
    list_display = ("id", "variant_display", "invoice_id", "quantity")
    list_filter = ("invoice",)
    search_fields = ("variant__sku", "variant__product__name", "invoice__title")
    autocomplete_fields = ("variant", "invoice")
    ordering = ("invoice", "variant")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("variant", "variant__product", "invoice")

    def variant_display(self, obj):
        if obj.variant:
            return f"{obj.variant.product.name} - {obj.variant.sku}"
        return "-"
    variant_display.short_description = "Variant"

    def invoice_id(self, obj):
        return f"Invoice #{obj.invoice.id}" if obj.invoice else "-"
    invoice_id.short_description = "Invoice"
