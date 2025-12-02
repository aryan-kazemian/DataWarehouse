from django.contrib import admin
from .models import DimDate, DimProductBase, DimVariantOrder, DimUser, FactSales


# -------------------------------
# Editable Admin Base Class
# -------------------------------
class EditableAdmin(admin.ModelAdmin):
    """
    Base class for fully editable admin
    """
    # You can still keep a default list of readonly fields if needed
    readonly_fields = []  # empty list means no fields are read-only


# -------------------------------
# Register Models with EditableAdmin
# -------------------------------

@admin.register(DimDate)
class DimDateAdmin(EditableAdmin):
    list_display = ('full_date', 'day_of_week', 'month_name', 'quarter', 'is_holiday')
    search_fields = ('full_date', 'day_of_week', 'month_name')


@admin.register(DimProductBase)
class DimProductBaseAdmin(EditableAdmin):
    list_display = ('product_id', 'name', 'brand', 'price', 'is_available', 'created_at', 'updated_at')
    search_fields = ('name', 'brand')
    list_filter = ('is_available', 'is_exciting', 'free_shipping', 'has_gift', 'is_budget_friendly')


@admin.register(DimVariantOrder)
class DimVariantOrderAdmin(EditableAdmin):
    list_display = ('variant_sku', 'product_id', 'color', 'size', 'quantity', 'unit_price', 'discount_percent', 'total_price', 'total_after_discount', 'created_at', 'updated_at')
    search_fields = ('variant_sku',)
    list_filter = ('color', 'size')


@admin.register(DimUser)
class DimUserAdmin(EditableAdmin):
    list_display = ('user_id', 'username', 'gender', 'city', 'registration_date', 'age_range')
    search_fields = ('username', 'city', 'gender')


@admin.register(FactSales)
class FactSalesAdmin(EditableAdmin):
    list_display = ('id', 'date', 'user', 'total_price', 'total_price_after_discount')
    search_fields = ('user__username', 'date__full_date')
    filter_horizontal = ('variants',)  # optional for M2M display
