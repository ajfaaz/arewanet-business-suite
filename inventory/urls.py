from django.urls import path
from inventory import views, api_views

urlpatterns = [
    path('grn/<int:pk>/', views.grn_detail, name='grn_detail'),
    path('gin/<int:pk>/', views.gin_detail, name='gin_detail'),
    path('transfer/<int:pk>/', views.transfer_detail, name='transfer_detail'),
    path('adjustment/<int:pk>/', views.adjustment_detail, name='adjustment_detail'),
    path('ledger/', api_views.StockLedgerAPIView.as_view(), name='stock-ledger-api'),
    path('ledger/summary/', api_views.StockLedgerSummaryAPIView.as_view(), name='stock-ledger-summary-api'),
    path('invoices/<int:invoice_id>/goods-issues/', api_views.InvoiceCreateGoodsIssueAPIView.as_view(), name='invoice-create-gin-api'),
    path('goods-issues/<int:pk>/submit/', api_views.GoodsIssueSubmitAPIView.as_view(), name='gin-submit-api'),
    path('goods-issues/<int:pk>/approve/', api_views.GoodsIssueApproveAPIView.as_view(), name='gin-approve-api'),
    path('goods-issues/<int:pk>/complete/', api_views.GoodsIssueCompleteAPIView.as_view(), name='gin-complete-api'),
]
