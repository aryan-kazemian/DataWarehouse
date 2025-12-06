from collections import defaultdict
from django.utils.dateparse import parse_date
from django.db.models import Sum, F, Count

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from .models import FactSales, DimVariantOrder, DimProductBase, FactAnalytics
from .serializers import (
    FactSalesVariantSerializer,
    FactAnalyticsSerializer,
    MostSoldProductSerializer,
    TopUserSerializer
)
from .filters import FactAnalyticsFilter, MostSoldProductsFilter, OrdersByStatusFilter, TopUsersFilter
from .sync_orders_analytics import sync_orders_analytics, verify_fact_sales_totals, simple_analysis
from .services import get_orders_by_status, get_top_users
from collections import defaultdict
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from .services import get_top_suppliers
from .serializers import TopSupplierSerializer
from .filters import TopSuppliersFilter
from .models import FactSales



class StandardResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100

class SimpleAnalysisAPI(APIView):
    filter_backends = [DjangoFilterBackend]
    filterset_class = FactAnalyticsFilter
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        try:
            simple_analysis()
            queryset = FactAnalytics.objects.select_related("date").all()
            filter_backend = DjangoFilterBackend()
            filtered_queryset = filter_backend.filter_queryset(request, queryset, self)
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(filtered_queryset, request)
            serializer = FactAnalyticsSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FactSalesListAPIView(APIView):
    def get(self, request):
        try:
            fact_sales_qs = FactSales.objects.select_related('date', 'user').prefetch_related('variants')
            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(fact_sales_qs, request)
            all_data = []
            product_ids = set()
            for fact in page:
                product_ids.update(v.product_id for v in fact.variants.all())
            products_map = {p.product_id: p for p in DimProductBase.objects.filter(product_id__in=product_ids)}
            for fact in page:
                for variant in fact.variants.all():
                    variant.product = products_map.get(variant.product_id)
                    all_data.append(FactSalesVariantSerializer(variant, context={'fact': fact}).data)
            return paginator.get_paginated_response(all_data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SyncOrdersAnalyticsAPI(APIView):
    def post(self, request):
        try:
            result = sync_orders_analytics()
            return Response({"message": "Sync completed successfully.", "details": result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyFactSalesTotalsAPI(APIView):
    def post(self, request):
        try:
            result = verify_fact_sales_totals()
            return Response({"message": "Verification completed.", "totals_match": result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OrdersByStatusAPI(APIView):
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrdersByStatusFilter

    def get(self, request):
        try:
            queryset = FactSales.objects.select_related('date', 'user')
            filter_backend = DjangoFilterBackend()
            filtered_queryset = filter_backend.filter_queryset(request, queryset, self)
            data = list(get_orders_by_status(queryset=filtered_queryset))
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TopUsersAPI(APIView):
    filter_backends = [DjangoFilterBackend]
    filterset_class = TopUsersFilter
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        try:
            queryset = FactSales.objects.select_related('date', 'user')
            filter_backend = DjangoFilterBackend()
            filtered_queryset = filter_backend.filter_queryset(request, queryset, self)
            raw_users = get_top_users(queryset=filtered_queryset)
            data = []
            for u in raw_users:
                data.append({
                    "user_id": u.get("user__user_id"),
                    "username": u.get("user__username"),
                    "gender": u.get("user__gender"),
                    "city": u.get("user__city"),
                    "registration_date": u.get("user__registration_date"),
                    "age_range": u.get("user__age_range"),
                    "total_orders": u.get("total_orders"),
                    "total_spent": u.get("total_spent"),
                })
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(data, request)
            serializer = TopUserSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MostSoldProductsAPI(APIView):
    filter_backends = [DjangoFilterBackend]
    filterset_class = MostSoldProductsFilter
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        try:
            queryset = FactSales.objects.prefetch_related('variants', 'date')
            filter_backend = DjangoFilterBackend()
            filtered_queryset = filter_backend.filter_queryset(request, queryset, self)
            variant_sales = (
                DimVariantOrder.objects
                .filter(factsales__in=filtered_queryset)
                .values('product_id')
                .annotate(
                    total_quantity_sold=Sum('quantity'),
                    total_sold_price=Sum(F('quantity') * F('unit_price')),
                    user_quantity=Count('factsales__user', distinct=True)
                )
                .order_by('-total_quantity_sold')
            )
            product_ids = [v['product_id'] for v in variant_sales if v['product_id'] is not None]
            products_map = {p.product_id: p for p in DimProductBase.objects.filter(product_id__in=product_ids)}
            per_date_agg = (
                FactSales.objects
                .filter(variants__product_id__in=product_ids)
                .values('variants__product_id', 'date__full_date')
                .annotate(
                    quantity=Sum('variants__quantity'),
                    users=Count('user', distinct=True)
                )
                .order_by('date__full_date')
            )
            per_date_map = defaultdict(list)
            for item in per_date_agg:
                per_date_map[item['variants__product_id']].append({
                    "date": item['date__full_date'],
                    "quantity": item['quantity'],
                    "users": item['users']
                })
            data = []
            for idx, v in enumerate(variant_sales, start=1):
                product = products_map.get(v['product_id'])
                per_date_list = per_date_map.get(v['product_id'], [])
                data.append({
                    "rank": idx,
                    "product_id": product.product_id if product else v['product_id'],
                    "product_name": product.name if product else "Unknown",
                    "brand": product.brand if product else None,
                    "supplier": product.supplier if product else None,
                    "category_level_1": product.category_level_1 if product else None,
                    "category_level_2": product.category_level_2 if product else None,
                    "category_level_3": product.category_level_3 if product else None,
                    "rating": product.rating if product else None,
                    "price": product.price if product else None,
                    "expire_date": product.expire_date if product else None,
                    "is_available": product.is_available if product else None,
                    "is_exciting": product.is_exciting if product else None,
                    "free_shipping": product.free_shipping if product else None,
                    "has_gift": product.has_gift if product else None,
                    "is_budget_friendly": product.is_budget_friendly if product else None,
                    "total_quantity_sold": v['total_quantity_sold'],
                    "total_sold_price": v['total_sold_price'],
                    "user_quantity": v['user_quantity'],
                    "per_date": per_date_list,
                })
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(data, request)
            serializer = MostSoldProductSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TopSuppliersAPI(APIView):
    filter_backends = [DjangoFilterBackend]
    filterset_class = TopSuppliersFilter
    pagination_class = StandardResultsSetPagination  # Use your custom pagination

    def get(self, request):
        try:
            queryset = FactSales.objects.prefetch_related('variants', 'date', 'user')
            filtered_queryset = DjangoFilterBackend().filter_queryset(request, queryset, self)

            supplier_data = get_top_suppliers(queryset=filtered_queryset)

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(supplier_data, request, view=self)  # pass view=self
            serializer = TopSupplierSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
