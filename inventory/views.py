from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from invoices.views import _get_user_organization
from inventory.models import GoodsReceivedNote, GoodsIssueNote, StockTransferDocument, StockAdjustmentDocument
from core.documents.context_builder import DocumentContextBuilder


@login_required
def grn_detail(request, pk):
    org = _get_user_organization(request.user)
    grn = get_object_or_404(GoodsReceivedNote.objects.select_related("warehouse", "purchase_order").prefetch_related("items__product"), pk=pk, organization=org)
    context = DocumentContextBuilder.build(
        grn,
        title=f"GRN #{grn.document_number}",
        extra_context={
            "doc_type": "GOODS RECEIVED NOTE",
            "warehouse": grn.warehouse,
            "supplier": getattr(grn.purchase_order, "supplier", None),
        }
    )
    return render(request, "documents/grn/detail.html", context)


@login_required
def gin_detail(request, pk):
    org = _get_user_organization(request.user)
    gin = get_object_or_404(GoodsIssueNote.objects.select_related("warehouse").prefetch_related("items__product"), pk=pk, organization=org)
    context = DocumentContextBuilder.build(
        gin,
        title=f"GIN #{gin.document_number}",
        extra_context={
            "doc_type": "GOODS ISSUE NOTE",
            "warehouse": gin.warehouse,
        }
    )
    return render(request, "documents/gin/detail.html", context)


@login_required
def transfer_detail(request, pk):
    org = _get_user_organization(request.user)
    transfer = get_object_or_404(StockTransferDocument.objects.select_related("source_warehouse", "destination_warehouse").prefetch_related("items__product"), pk=pk, organization=org)
    context = DocumentContextBuilder.build(
        transfer,
        title=f"Transfer #{transfer.document_number}",
        extra_context={
            "doc_type": "STOCK TRANSFER",
        }
    )
    return render(request, "documents/transfer/detail.html", context)


@login_required
def adjustment_detail(request, pk):
    org = _get_user_organization(request.user)
    adj = get_object_or_404(StockAdjustmentDocument.objects.select_related("warehouse").prefetch_related("items__product"), pk=pk, organization=org)
    context = DocumentContextBuilder.build(
        adj,
        title=f"Adjustment #{adj.document_number}",
        extra_context={
            "doc_type": "STOCK ADJUSTMENT",
            "warehouse": adj.warehouse,
        }
    )
    return render(request, "documents/adjustment/detail.html", context)
