from decimal import Decimal
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q, Count

from invoices.permissions import require_permission
from invoices.views import _get_user_organization
from invoices.models import Product, ActivityLog
from inventory.models import Warehouse
from purchases.models import Supplier, PurchaseOrder, PurchaseOrderItem
from purchases.selectors import SupplierSelector, PurchaseOrderSelector
from purchases.services import SupplierService, PurchaseService
from purchases.forms import SupplierForm, PurchaseOrderForm


@login_required
@require_permission("supplier.view")
def supplier_list(request):
    organization = _get_user_organization(request.user)
    query = request.GET.get("q", "").strip()

    suppliers = SupplierSelector.list(organization)
    if query:
        suppliers = suppliers.filter(
            Q(company_name__icontains=query) |
            Q(code__icontains=query) |
            Q(email__icontains=query) |
            Q(contact_person__icontains=query)
        )

    active_count = suppliers.filter(is_active=True).count()
    total_count = suppliers.count()

    return render(request, "purchases/supplier_list.html", {
        "suppliers": suppliers,
        "query": query,
        "active_count": active_count,
        "total_count": total_count,
        "title": "Suppliers Directory",
    })


@login_required
@require_permission("supplier.create")
def supplier_create(request):
    organization = _get_user_organization(request.user)

    if request.method == "POST":
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = SupplierService.create_supplier(
                organization=organization,
                data=form.cleaned_data
            )
            ActivityLog.objects.create(
                user=request.user,
                action=f"Created supplier '{supplier.company_name}' ({supplier.code})"
            )
            messages.success(request, f"Supplier '{supplier.company_name}' created successfully.")
            return redirect("supplier_list")
    else:
        form = SupplierForm()

    return render(request, "purchases/supplier_form.html", {
        "form": form,
        "title": "New Supplier Registration",
    })


@login_required
@require_permission("supplier.edit")
def supplier_edit(request, pk):
    organization = _get_user_organization(request.user)
    supplier = get_object_or_404(Supplier, pk=pk, organization=organization)

    if request.method == "POST":
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            SupplierService.update_supplier(
                supplier=supplier,
                data=form.cleaned_data
            )
            ActivityLog.objects.create(
                user=request.user,
                action=f"Updated supplier '{supplier.company_name}' ({supplier.code})"
            )
            messages.success(request, f"Supplier '{supplier.company_name}' updated successfully.")
            return redirect("supplier_list")
    else:
        form = SupplierForm(instance=supplier)

    return render(request, "purchases/supplier_form.html", {
        "form": form,
        "supplier": supplier,
        "title": f"Edit Supplier — {supplier.company_name}",
    })


@login_required
@require_permission("supplier.delete")
def supplier_delete(request, pk):
    organization = _get_user_organization(request.user)
    supplier = get_object_or_404(Supplier, pk=pk, organization=organization)

    if request.method == "POST":
        name = supplier.company_name
        supplier.is_active = False
        supplier.save(update_fields=["is_active"])
        messages.success(request, f"Supplier '{name}' has been deactivated.")
        return redirect("supplier_list")

    return render(request, "purchases/supplier_confirm_delete.html", {
        "supplier": supplier,
        "title": f"Deactivate Supplier — {supplier.company_name}",
    })


@login_required
@require_permission("purchase_order.view")
def purchase_order_list(request):
    organization = _get_user_organization(request.user)
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    orders = PurchaseOrderSelector.list(organization)

    if status_filter:
        orders = orders.filter(status=status_filter)

    if query:
        orders = orders.filter(
            Q(order_number__icontains=query) |
            Q(supplier__company_name__icontains=query) |
            Q(warehouse__name__icontains=query)
        )

    stats = {
        "total_orders": orders.count(),
        "draft_count": orders.filter(status="DRAFT").count(),
        "approved_count": orders.filter(status="APPROVED").count(),
        "total_value": orders.aggregate(val=Sum("total"))["val"] or Decimal("0.00"),
    }

    return render(request, "purchases/purchase_order_list.html", {
        "orders": orders,
        "query": query,
        "status_filter": status_filter,
        "stats": stats,
        "status_choices": PurchaseOrder.STATUS_CHOICES,
        "title": "Purchase Orders",
    })


@login_required
@require_permission("purchase_order.create")
def purchase_order_create(request):
    organization = _get_user_organization(request.user)

    if request.method == "POST":
        form = PurchaseOrderForm(request.POST, organization=organization)
        product_ids = request.POST.getlist("product_id[]")
        quantities = request.POST.getlist("quantity[]")
        unit_costs = request.POST.getlist("unit_cost[]")

        items_data = []
        for pid, qty, cost in zip(product_ids, quantities, unit_costs):
            if pid and qty and cost:
                try:
                    p = Product.objects.get(pk=int(pid), organization=organization)
                    items_data.append({
                        "product": p,
                        "quantity": Decimal(str(qty)),
                        "unit_cost": Decimal(str(cost)),
                    })
                except (ValueError, Product.DoesNotExist):
                    continue

        if form.is_valid():
            if not items_data:
                messages.error(request, "Please add at least one valid line item to the purchase order.")
            else:
                po = PurchaseService.create_purchase_order(
                    organization=organization,
                    supplier=form.cleaned_data["supplier"],
                    warehouse=form.cleaned_data["warehouse"],
                    items_data=items_data,
                    order_date=form.cleaned_data.get("order_date"),
                    expected_date=form.cleaned_data.get("expected_date"),
                    notes=form.cleaned_data.get("notes", ""),
                    user=request.user
                )
                ActivityLog.objects.create(
                    user=request.user,
                    action=f"Created Purchase Order {po.order_number} for '{po.supplier.company_name}'"
                )
                messages.success(request, f"Purchase Order '{po.order_number}' created successfully.")
                return redirect("purchase_order_detail", pk=po.pk)
    else:
        form = PurchaseOrderForm(organization=organization, initial={"order_date": date.today()})

    products = Product.objects.filter(organization=organization, is_active=True).order_by("name")

    return render(request, "purchases/purchase_order_form.html", {
        "form": form,
        "products": products,
        "title": "Create Purchase Order",
    })


@login_required
@require_permission("purchase_order.view")
def purchase_order_detail(request, pk):
    organization = _get_user_organization(request.user)
    po = get_object_or_404(
        PurchaseOrder.objects.select_related("supplier", "warehouse", "created_by").prefetch_related("items__product"),
        pk=pk,
        organization=organization
    )

    return render(request, "purchases/purchase_order_detail.html", {
        "po": po,
        "title": f"Purchase Order {po.order_number}",
    })


@login_required
@require_permission("purchase_order.create")
def purchase_order_submit(request, pk):
    organization = _get_user_organization(request.user)
    po = get_object_or_404(PurchaseOrder, pk=pk, organization=organization)

    if request.method == "POST":
        try:
            PurchaseService.submit_purchase_order(po, user=request.user)
            messages.success(request, f"Purchase Order {po.order_number} submitted for approval.")
        except Exception as e:
            messages.error(request, str(e))

    return redirect("purchase_order_detail", pk=po.pk)


@login_required
@require_permission("purchase_order.approve")
def purchase_order_approve(request, pk):
    organization = _get_user_organization(request.user)
    po = get_object_or_404(PurchaseOrder, pk=pk, organization=organization)

    if request.method == "POST":
        try:
            PurchaseService.approve_purchase_order(po, user=request.user)
            messages.success(request, f"Purchase Order {po.order_number} approved.")
        except Exception as e:
            messages.error(request, str(e))

    return redirect("purchase_order_detail", pk=po.pk)


@login_required
@require_permission("purchase_order.create")
def purchase_order_cancel(request, pk):
    organization = _get_user_organization(request.user)
    po = get_object_or_404(PurchaseOrder, pk=pk, organization=organization)

    if request.method == "POST":
        try:
            PurchaseService.cancel_purchase_order(po, user=request.user)
            messages.warning(request, f"Purchase Order {po.order_number} cancelled.")
        except Exception as e:
            messages.error(request, str(e))

    return redirect("purchase_order_detail", pk=po.pk)


@login_required
@require_permission("purchase_order.create")
def purchase_order_close(request, pk):
    organization = _get_user_organization(request.user)
    po = get_object_or_404(PurchaseOrder, pk=pk, organization=organization)

    if request.method == "POST":
        try:
            PurchaseService.close_purchase_order(po, user=request.user)
            messages.info(request, f"Purchase Order {po.order_number} marked as closed.")
        except Exception as e:
            messages.error(request, str(e))

    return redirect("purchase_order_detail", pk=po.pk)
