import django_filters
from .models import FactAnalytics, FactSales

class FactAnalyticsFilter(django_filters.FilterSet):
    start = django_filters.DateFilter(field_name="date__full_date", lookup_expr="gte")
    end = django_filters.DateFilter(field_name="date__full_date", lookup_expr="lte")
    jalali_date = django_filters.CharFilter(field_name="date__jalali_date", lookup_expr="icontains")
    day_of_week = django_filters.CharFilter(field_name="date__day_of_week", lookup_expr="iexact")
    month_name = django_filters.CharFilter(field_name="date__month_name", lookup_expr="iexact")
    quarter = django_filters.NumberFilter(field_name="date__quarter")
    is_holiday = django_filters.BooleanFilter(field_name="date__is_holiday")
    class Meta:
        model = FactAnalytics
        fields = []

class MostSoldProductsFilter(django_filters.FilterSet):
    start = django_filters.DateFilter(field_name="date__full_date", lookup_expr="gte")
    end = django_filters.DateFilter(field_name="date__full_date", lookup_expr="lte")
    day_of_week = django_filters.CharFilter(field_name="date__day_of_week", lookup_expr="iexact")
    month_name = django_filters.CharFilter(field_name="date__month_name", lookup_expr="iexact")
    is_holiday = django_filters.BooleanFilter(field_name="date__is_holiday")
    supplier = django_filters.CharFilter(field_name="variants__product__supplier", lookup_expr="icontains")
    class Meta:
        model = FactSales
        fields = []

class OrdersByStatusFilter(django_filters.FilterSet):
    start = django_filters.DateFilter(field_name="date__full_date", lookup_expr="gte")
    end = django_filters.DateFilter(field_name="date__full_date", lookup_expr="lte")
    class Meta:
        model = FactSales
        fields = []

class TopUsersFilter(django_filters.FilterSet):
    start = django_filters.DateFilter(field_name="date__full_date", lookup_expr="gte", required=False)
    end = django_filters.DateFilter(field_name="date__full_date", lookup_expr="lte", required=False)
    day_of_week = django_filters.CharFilter(field_name="date__day_of_week", lookup_expr="iexact")
    month_name = django_filters.CharFilter(field_name="date__month_name", lookup_expr="iexact")
    is_holiday = django_filters.BooleanFilter(field_name="date__is_holiday")
    city = django_filters.CharFilter(field_name="user__city", lookup_expr="iexact")
    gender = django_filters.CharFilter(field_name="user__gender", lookup_expr="iexact")
    age_range = django_filters.CharFilter(field_name="user__age_range", lookup_expr="iexact")
    username = django_filters.CharFilter(field_name="user__username", lookup_expr="icontains")
    class Meta:
        model = FactSales
        fields = []


class TopSuppliersFilter(django_filters.FilterSet):
    start = django_filters.DateFilter(field_name="date__full_date", lookup_expr="gte", required=False)
    end = django_filters.DateFilter(field_name="date__full_date", lookup_expr="lte", required=False)
    supplier_name = django_filters.CharFilter(field_name="variants__product__supplier", lookup_expr="icontains")

    class Meta:
        model = FactSales
        fields = []