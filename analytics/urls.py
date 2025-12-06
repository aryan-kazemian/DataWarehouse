from django.urls import path
from .views import (
                        SyncOrdersAnalyticsAPI,
                        VerifyFactSalesTotalsAPI,
                        FactSalesListAPIView,
                        SimpleAnalysisAPI,
                        TopUsersAPI,
                        OrdersByStatusAPI,
                        MostSoldProductsAPI,
                        TopSuppliersAPI
                    )

    

urlpatterns = [
    path('sync-orders-analytics/', SyncOrdersAnalyticsAPI.as_view(), name='sync_orders_analytics'),
    path('verify-totals/', VerifyFactSalesTotalsAPI.as_view(), name='verify_fact_sales_totals'),
    path('fact-sales/', FactSalesListAPIView.as_view(), name='fact_sales_list'),
    path('simple-analysis/', SimpleAnalysisAPI.as_view(), name='simple_analysis'),
    path("most-sold/", MostSoldProductsAPI.as_view()),
    path("orders-by-status/", OrdersByStatusAPI.as_view()),
    path("top-users/", TopUsersAPI.as_view()),
    path("top-suppliers/", TopSuppliersAPI.as_view(), name="top_suppliers"),
]
