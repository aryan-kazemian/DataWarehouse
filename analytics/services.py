from django.db.models import Sum, F, Count
from .models import FactSales, DimVariantOrder
from collections import defaultdict
from django.db.models import Sum, F, Count
from .models import FactSales, DimVariantOrder, DimProductBase

def get_most_sold_products(start=None, end=None, queryset=None):
    if queryset is None:
        queryset = FactSales.objects.all()
        if start:
            queryset = queryset.filter(date__full_date__gte=start)
        if end:
            queryset = queryset.filter(date__full_date__lte=end)
    return (
        queryset.values("variants__product_id")
        .annotate(total_qty=Sum("variants__quantity"))
        .order_by("-total_qty")
    )

def get_orders_by_status(start=None, end=None, queryset=None):
    if queryset is None:
        queryset = FactSales.objects.all()
        if start:
            queryset = queryset.filter(date__full_date__gte=start)
        if end:
            queryset = queryset.filter(date__full_date__lte=end)
    return queryset.values("status").annotate(total=Sum("total_price_after_discount"))

def get_top_users(queryset=None, start=None, end=None):
    if queryset is None:
        queryset = FactSales.objects.all()
        if start:
            queryset = queryset.filter(date__full_date__gte=start)
        if end:
            queryset = queryset.filter(date__full_date__lte=end)
    return queryset.values(
        "user__user_id",
        "user__username",
        "user__gender",
        "user__city",
        "user__registration_date",
        "user__age_range"
    ).annotate(
        total_orders=Count("id"),
        total_spent=Sum("total_price_after_discount")
    ).order_by("-total_orders")

def get_top_suppliers(start=None, end=None, queryset=None):
    if queryset is None:
        queryset = FactSales.objects.all()
        if start:
            queryset = queryset.filter(date__full_date__gte=start)
        if end:
            queryset = queryset.filter(date__full_date__lte=end)

    # Get all variant IDs in the filtered FactSales
    variant_ids = DimVariantOrder.objects.filter(factsales__in=queryset).values_list('id', flat=True)

    # Join with DimProductBase manually
    variant_sales = (
        DimVariantOrder.objects
        .filter(id__in=variant_ids)
        .values('product_id')
        .annotate(
            total_quantity_sold=Sum('quantity'),
            total_sold_price=Sum(F('quantity') * F('unit_price')),
            user_quantity=Count('factsales__user', distinct=True)
        )
    )

    # Map product_id → supplier
    product_ids = [v['product_id'] for v in variant_sales if v['product_id'] is not None]
    products_map = {p.product_id: p for p in DimProductBase.objects.filter(product_id__in=product_ids)}

    # Aggregate by supplier
    supplier_agg = defaultdict(lambda: {'total_quantity_sold': 0, 'total_sold_price': 0, 'user_quantity': 0})
    for v in variant_sales:
        product = products_map.get(v['product_id'])
        supplier_name = product.supplier if product else "Unknown"
        supplier_agg[supplier_name]['total_quantity_sold'] += v['total_quantity_sold']
        supplier_agg[supplier_name]['total_sold_price'] += v['total_sold_price']
        supplier_agg[supplier_name]['user_quantity'] += v['user_quantity']

    # Convert to list and sort by total_quantity_sold
    result = [
        {
            'supplier': k,
            'total_quantity_sold': v['total_quantity_sold'],
            'total_sold_price': v['total_sold_price'],
            'user_quantity': v['user_quantity'],
        }
        for k, v in supplier_agg.items()
    ]
    result.sort(key=lambda x: x['total_quantity_sold'], reverse=True)
    return result