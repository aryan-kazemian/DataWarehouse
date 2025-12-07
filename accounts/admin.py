from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, AgeRange

@admin.register(AgeRange)
class AgeRangeAdmin(admin.ModelAdmin):
    list_display = ("name", "min_age", "max_age", "slug")
    search_fields = ("name",)
    readonly_fields = ("slug",)
    ordering = ("min_age",)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "gender",
        "age_range_name",
        "city",
        "registration_date",
        "is_staff",
        "is_active",
    )
    list_filter = ("gender", "age_range", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name", "city")
    readonly_fields = ("registration_date",)
    fieldsets = (
        ("Authentication", {"fields": ("username", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "email", "gender", "age_range", "city")}),
        ("Permissions", {"fields": ("is_staff", "is_active", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "registration_date")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2", "gender", "age_range", "city", "is_staff", "is_active"),
        }),
    )
    ordering = ("username",)
    filter_horizontal = ("groups", "user_permissions")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("age_range")

    def age_range_name(self, obj):
        return obj.age_range.name if obj.age_range else "-"
    age_range_name.admin_order_field = "age_range"
    age_range_name.short_description = "Age Range"
