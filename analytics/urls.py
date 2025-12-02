from django.urls import path
from .views import SyncOrdersAnalyticsAPI, VerifyFactSalesTotalsAPI

urlpatterns = [
    path('', SyncOrdersAnalyticsAPI.as_view(), name='sync_orders_analytics'),
    path('verify-totals/', VerifyFactSalesTotalsAPI.as_view(), name='verify_fact_sales_totals'),
]
