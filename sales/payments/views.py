from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from invoices.views import _get_user_organization, _check_permission
from invoices.models import Invoice, Customer, Organization
from sales.payments.models import Payment, PaymentAllocation
from sales.payments.forms import PaymentForm, MultiInvoicePaymentForm
from sales.payments.services import PaymentService
from sales.payments.selectors import PaymentSelectors


@login_required
def payment_dashboard(request):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT', 'STAFF'])
    org = _get_user_organization(request.user)

    stats = PaymentSelectors.get_payment_center_stats(org)
    analytics = PaymentSelectors.get_payment_analytics(org)
    recent_payments = Payment.objects.filter(
        organization=org
    ).select_related('customer', 'invoice').order_by('-payment_date', '-created_at')[:10]

    return render(
        request,
        'payments/payment_dashboard.html',
        {
            'stats': stats,
            'analytics': analytics,
            'recent_payments': recent_payments,
        }
    )


@login_required
def payment_list(request):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT', 'STAFF'])
    org = _get_user_organization(request.user)

    payments = Payment.objects.filter(
        organization=org
    ).select_related('customer', 'invoice').order_by('-payment_date', '-created_at')

    # Filtering
    method_filter = request.GET.get('method')
    status_filter = request.GET.get('status')
    search_query = request.GET.get('q')

    if method_filter:
        payments = payments.filter(payment_method=method_filter)
    if status_filter:
        payments = payments.filter(status=status_filter)
    if search_query:
        payments = payments.filter(
            receipt_number__icontains=search_query
        ) | payments.filter(
            customer__company_name__icontains=search_query
        ) | payments.filter(
            reference__icontains=search_query
        )

    return render(
        request,
        'payments/payment_list.html',
        {
            'payments': payments,
            'selected_method': method_filter,
            'selected_status': status_filter,
            'search_query': search_query,
        }
    )


@login_required
def receive_payment(request, invoice_id=None):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)

    invoice = None
    if invoice_id:
        invoice = get_object_or_404(Invoice, pk=invoice_id, organization=org)

    if request.method == 'POST':
        post_data = request.POST.copy()
        if invoice and not post_data.get('customer'):
            post_data['customer'] = str(invoice.customer.pk)
        form = PaymentForm(post_data, organization=org)
        if form.is_valid():
            customer = form.cleaned_data.get('customer') or (invoice.customer if invoice else None)
            amount = form.cleaned_data['amount']
            payment_method = form.cleaned_data['payment_method']
            payment_date = form.cleaned_data['payment_date']
            reference = form.cleaned_data['reference']
            notes = form.cleaned_data['notes']

            payment = PaymentService.receive_payment(
                organization=org,
                customer=customer,
                amount=amount,
                payment_method=payment_method,
                payment_date=payment_date,
                reference=reference,
                notes=notes,
                invoice=invoice,
                user=request.user
            )

            messages.success(request, f"Payment {payment.receipt_number} recorded successfully.")

            if request.headers.get('HX-Request') or request.GET.get('modal'):
                return redirect('invoice_detail', pk=invoice.pk) if invoice else redirect('payment_detail', pk=payment.pk)

            return redirect('payment_detail', pk=payment.pk)
    else:
        initial_data = {}
        if invoice:
            initial_data['customer'] = invoice.customer
            initial_data['amount'] = invoice.balance_due
        form = PaymentForm(organization=org, initial=initial_data)

    is_modal = request.GET.get('modal') == '1' or request.headers.get('HX-Request')
    template_name = 'payments/receive_payment_modal.html' if is_modal else 'payments/receive_payment.html'

    return render(
        request,
        template_name,
        {
            'form': form,
            'invoice': invoice,
        }
    )


@login_required
def multi_invoice_payment(request):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)

    if request.method == 'POST':
        form = MultiInvoicePaymentForm(request.POST, organization=org)
        if form.is_valid():
            customer = form.cleaned_data['customer']
            amount = form.cleaned_data['amount']
            payment_method = form.cleaned_data['payment_method']
            payment_date = form.cleaned_data['payment_date']
            reference = form.cleaned_data['reference']
            notes = form.cleaned_data['notes']

            selected_invoice_ids = request.POST.getlist('selected_invoices')

            payment = PaymentService.allocate_multi_invoice_payment(
                organization=org,
                customer=customer,
                amount=amount,
                payment_method=payment_method,
                payment_date=payment_date,
                selected_invoice_ids=[int(i) for i in selected_invoice_ids if i.isdigit()],
                reference=reference,
                notes=notes,
                user=request.user
            )

            messages.success(request, f"Multi-Invoice Payment {payment.receipt_number} allocated successfully.")
            return redirect('payment_detail', pk=payment.pk)
    else:
        form = MultiInvoicePaymentForm(organization=org)

    open_invoices = Invoice.objects.filter(
        organization=org
    ).exclude(status__in=['PAID', 'CANCELLED', 'DRAFT']).select_related('customer').order_by('customer', 'due_date')

    return render(
        request,
        'payments/multi_invoice_payment.html',
        {
            'form': form,
            'open_invoices': open_invoices,
        }
    )


import uuid
from django.db.models import Q

def _get_payment_by_pk(pk, org):
    is_valid_uuid = False
    try:
        uuid.UUID(str(pk))
        is_valid_uuid = True
    except (ValueError, TypeError):
        pass

    if is_valid_uuid:
        p = Payment.objects.filter(organization=org, uuid=pk).select_related('customer', 'invoice', 'organization', 'created_by').prefetch_related('allocations__invoice').first()
        if p:
            return p
    if str(pk).isdigit():
        p = Payment.objects.filter(organization=org, id=int(pk)).first()
        if p:
            return p
        from invoices.models import Payment as LegacyPayment
        p = LegacyPayment.objects.filter(organization=org, id=int(pk)).first()
        if p:
            return p
    return get_object_or_404(Payment, pk=pk, organization=org)


@login_required
def payment_detail(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT', 'STAFF'])
    org = _get_user_organization(request.user)

    payment = _get_payment_by_pk(pk, org)

    return render(
        request,
        'payments/payment_detail.html',
        {
            'payment': payment,
            'invoice': payment.invoice,
            'organization': payment.organization,
        }
    )


@login_required
def receipt_view(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT', 'STAFF'])
    org = _get_user_organization(request.user)

    payment = _get_payment_by_pk(pk, org)

    return render(
        request,
        'payments/receipt.html',
        {
            'payment': payment,
            'organization': payment.organization,
        }
    )


@login_required
def payment_reverse(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN'])
    org = _get_user_organization(request.user)

    payment = _get_payment_by_pk(pk, org)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        PaymentService.reverse_payment(payment, reason=reason, user=request.user)
        messages.success(request, f"Payment {payment.receipt_number} reversed successfully.")
        return redirect('payment_detail', pk=payment.pk)

    return render(
        request,
        'payments/payment_confirm_reverse.html',
        {'payment': payment}
    )


@login_required
def payment_refund(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN'])
    org = _get_user_organization(request.user)

    payment = _get_payment_by_pk(pk, org)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        PaymentService.refund_payment(payment, reason=reason, user=request.user)
        messages.success(request, f"Payment {payment.receipt_number} refunded successfully.")
        return redirect('payment_detail', pk=payment.pk)

    return render(
        request,
        'payments/payment_confirm_refund.html',
        {'payment': payment}
    )
