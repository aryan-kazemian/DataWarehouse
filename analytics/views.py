from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .sync_orders_analytics import sync_orders_analytics, verify_fact_sales_totals

class SyncOrdersAnalyticsAPI(APIView):

    def post(self, request):
        try:
            result = sync_orders_analytics()
            return Response(
                {"message": "Sync completed successfully.", "details": result},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyFactSalesTotalsAPI(APIView):
    def post(self, request):
        try:
            result = verify_fact_sales_totals()
            return Response(
                {"message": "Verification completed.", "totals_match": result},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)