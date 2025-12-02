from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin
from .models import Brand, Category, Product, Variant

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


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 1
    fields = ("sku", "color", "size")
    show_change_link = True


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "brand",
        "category",
        "price",
        "rating",
        "is_available",
        "is_exciting",
        "free_shipping",
        "has_gift",
        "is_budget_friendly",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "brand",
        "category",
        "is_available",
        "is_exciting",
        "free_shipping",
        "has_gift",
        "is_budget_friendly",
    )
    search_fields = ("name", "brand__name", "category__name")
    inlines = [VariantInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "product",
        "color",
        "size",
        "created_at",
        "updated_at",
    )
    list_filter = ("product", "color", "size")
    search_fields = ("sku", "product__name", "color", "size")
    readonly_fields = ("created_at", "updated_at")
