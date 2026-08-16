import io
from decimal import Decimal
from datetime import date, datetime
from django.contrib.auth import logout as auth_logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse, Http404
from django.db.models import Sum, Q
from django.core.mail import EmailMessage
from django.contrib import messages

from .models import Invoice, InvoiceItem, Quotation, Organization, Customer, UserProfile, ActivityLog, Payment, Receipt, ProductCategory, Product, OrganizationMembership, QuotationTemplate
from .forms import InvoiceForm, InvoiceItemFormSet, CustomerForm, PaymentForm, ProductCategoryForm, ProductForm, QuotationForm, QuotationItemFormSet, QuotationTemplateForm
from .permissions import require_permission
from .services.quotation_template_service import QuotationTemplateService
from .utils.pdf_generator import generate_invoice_pdf



def user_logout(request):
    auth_logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')


@login_required
def switch_organization(request):
    if request.method == "POST":
        org_id = request.POST.get("organization_id")
        if org_id:
            membership = OrganizationMembership.objects.filter(
                user=request.user,
                organization_id=org_id,
                is_active=True,
            ).first()
            if membership:
                request.session['active_organization_id'] = membership.organization.id
                messages.success(request, f"Switched active organization to {membership.organization.name}.")
            else:
                messages.error(request, "You do not have active access to that organization.")
                raise PermissionDenied("Unauthorized organization access attempt.")

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "dashboard"
    return redirect(next_url)


def _get_user_organization(user):
    if not user or not user.is_authenticated:
        org = Organization.objects.first()
        if not org:
            org = Organization.objects.create(name='ArewaNet Ventures', slug='arewanet-ventures')
        return org

    if hasattr(user, 'organization_memberships'):
        active_m = user.organization_memberships.filter(is_active=True).first()
        if active_m and active_m.organization:
            return active_m.organization

    if hasattr(user, 'userprofile') and user.userprofile.organization:
        return user.userprofile.organization

    org = Organization.objects.first()
    if not org:
        org = Organization.objects.create(name='ArewaNet Ventures', slug='arewanet-ventures')
    return org


get_user_organization = _get_user_organization


def _check_permission(user, allowed_roles, request=None):
    if user.is_superuser:
        return

    membership = getattr(request, 'membership', None) if request else None
    if not membership and hasattr(user, 'organization_memberships'):
        membership = user.organization_memberships.filter(is_active=True).first()

    if membership and membership.is_active:
        if membership.role and membership.role.slug == 'administrator':
            return
        if isinstance(allowed_roles, str):
            norm = allowed_roles.replace('_', '.')
            if membership.has_permission(norm) or membership.has_permission(allowed_roles):
                return
        elif isinstance(allowed_roles, (list, tuple)):
            if membership.role and (membership.role.slug in [r.lower().replace(' ', '-') for r in allowed_roles] or membership.role.name.upper() in [r.upper() for r in allowed_roles]):
                return
            for code in allowed_roles:
                norm = str(code).replace('_', '.')
                if membership.has_permission(norm) or membership.has_permission(str(code)):
                    return

    if hasattr(user, 'userprofile') and user.userprofile.role in allowed_roles:
        return

    raise PermissionDenied("Unauthorized access attempt.")



@login_required
def dashboard(request):
    org = getattr(request, 'organization', None) or _get_user_organization(request.user)
    membership = getattr(request, 'membership', None)
    period = request.GET.get('period', 'month')
    from invoices.services.dashboard_service import DashboardService
    service = DashboardService(organization=org)
    dashboard_data = service.get_dashboard_data(membership=membership, period=period)

    context = {
        'kpis': dashboard_data['kpis'],
        'actions': dashboard_data.get('actions', {}),
        'analytics': dashboard_data.get('analytics', {}),
        'recent_activity': dashboard_data['recent_activity'],
        'customer_count': dashboard_data['kpis'].get('customers', {}).get('count', 0),
        'supplier_count': dashboard_data['kpis'].get('suppliers', {}).get('count', 0),
        'product_count': dashboard_data['kpis'].get('products', {}).get('total_count', 0),
        'invoice_summary': dashboard_data['kpis'].get('invoices', {}),
        'payment_summary': dashboard_data['kpis'].get('payments', {}),
        'quotation_summary': dashboard_data['kpis'].get('quotations', {}),
        'recent_invoices': dashboard_data['recent_activity'].get('invoices', []),
        'recent_quotations': dashboard_data['recent_activity'].get('quotations', []),
        'recent_payments': dashboard_data['recent_activity'].get('payments', []),
    }

    if 'payments' in dashboard_data['kpis']:
        context['total_revenue'] = dashboard_data['kpis']['payments']['total_received']
        context['revenue'] = dashboard_data['kpis']['payments']['total_received']
    if 'invoices' in dashboard_data['kpis']:
        context['outstanding'] = dashboard_data['kpis']['invoices']['outstanding']
        context['paid_count'] = dashboard_data['kpis']['invoices']['paid_count']
        context['paid'] = dashboard_data['kpis']['invoices']['paid_count']
        context['unpaid_count'] = dashboard_data['kpis']['invoices']['unpaid_count']
        context['unpaid'] = dashboard_data['kpis']['invoices']['unpaid_count']

    return render(
        request,
        'dashboard/dashboard.html',
        context
    )


@login_required
def global_search(request):
    org = _get_user_organization(request.user)
    query = request.GET.get('q', '')
    from sales.services.search_service import SearchService
    results = SearchService.global_search(query, organization=org)
    results['query'] = query
    return render(request, 'invoices/search_results.html', results)


@login_required
def invoice_list(request):
    org = _get_user_organization(request.user)
    status_filter = request.GET.get('status', 'all').lower()

    invoices = Invoice.objects.filter(organization=org).order_by('-id')

    if status_filter in ['paid', 'unpaid', 'overdue', 'draft']:
        invoices = invoices.filter(status__iexact=status_filter)

    return render(
        request,
        'invoices/invoice_list.html',
        {
            'invoices': invoices,
            'current_status': status_filter
        }
    )


@login_required
def invoice_detail(request, pk):
    org = _get_user_organization(request.user)
    invoice = get_object_or_404(
        Invoice.objects.select_related('customer', 'organization').prefetch_related('items'),
        pk=pk,
        organization=org
    )
    from core.documents.context_builder import DocumentContextBuilder
    from sales.payments.selectors import PaymentSelectors

    timeline_events = PaymentSelectors.get_payments_for_timeline(invoice)
    latest_payment = invoice.payments.order_by('-payment_date', '-id').first() if hasattr(invoice, 'payments') else None

    context = DocumentContextBuilder.build(
        invoice,
        title=f"Invoice #{invoice.invoice_no}",
        extra_context={
            "invoice": invoice,
            "customer": invoice.customer,
            "date": invoice.invoice_date,
            "due_date": invoice.due_date,
            "doc_type": "INVOICE",
            "timeline_events": timeline_events,
            "latest_payment": latest_payment,
            "total_paid": invoice.total_paid,
            "balance_due": invoice.balance,
        }
    )
    return render(request, "documents/invoice/detail.html", context)


@login_required
def invoice_pdf(request, pk):
    org = _get_user_organization(request.user)
    invoice = get_object_or_404(
        Invoice.objects.select_related('customer', 'organization').prefetch_related('items'),
        pk=pk,
        organization=org
    )
    from core.documents.context_builder import DocumentContextBuilder
    from django.template.loader import render_to_string

    context = DocumentContextBuilder.build(
        invoice,
        title=f"Invoice #{invoice.invoice_no}",
        extra_context={
            "invoice": invoice,
            "customer": invoice.customer,
            "date": invoice.invoice_date,
            "due_date": invoice.due_date,
            "doc_type": "INVOICE",
            "total_paid": invoice.total_paid,
            "balance_due": invoice.balance,
        }
    )
    html_content = render_to_string("documents/invoice/detail.html", context, request=request)
    
    try:
        from weasyprint import HTML
        pdf_file = HTML(string=html_content).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Invoice_{invoice.invoice_no}.pdf"'
        return response
    except Exception:
        response = HttpResponse(html_content.encode('utf-8'), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Invoice_{invoice.invoice_no}.pdf"'
        return response


@login_required
def invoice_duplicate(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)
    orig_invoice = get_object_or_404(Invoice, pk=pk, organization=org)

    new_invoice = Invoice.objects.create(
        organization=org,
        customer=orig_invoice.customer,
        invoice_date=date.today(),
        due_date=orig_invoice.due_date,
        project_name=orig_invoice.project_name,
        deployment_phase=orig_invoice.deployment_phase,
        subtotal=orig_invoice.subtotal,
        vat=orig_invoice.vat,
        total_due=orig_invoice.total_due,
        status='DRAFT'
    )

    for item in orig_invoice.items.all():
        InvoiceItem.objects.create(
            invoice=new_invoice,
            description=item.description,
            unit=item.unit,
            qty=item.qty,
            unit_price=item.unit_price,
            total=item.total
        )

    ActivityLog.objects.create(
        user=request.user,
        action=f"Invoice {orig_invoice.invoice_no} Duplicated to {new_invoice.invoice_no}"
    )

    return redirect('invoice_detail', new_invoice.id)


@login_required
def invoice_mark_paid(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)
    invoice = get_object_or_404(Invoice, pk=pk, organization=org)

    invoice.status = 'PAID'
    invoice.save()

    ActivityLog.objects.create(
        user=request.user,
        action=f"Invoice {invoice.invoice_no} Marked as Paid"
    )

    return redirect('invoice_detail', invoice.id)


@login_required
def invoice_delete(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN'])
    org = _get_user_organization(request.user)
    invoice = get_object_or_404(Invoice, pk=pk, organization=org)

    if request.method == 'POST':
        inv_no = invoice.invoice_no
        invoice.delete()
        ActivityLog.objects.create(
            user=request.user,
            action=f"Invoice {inv_no} Deleted"
        )
        return redirect('invoice_list')

    return render(
        request,
        'invoices/invoice_delete.html',
        {'invoice': invoice}
    )


@login_required
def payment_list(request):
    org = _get_user_organization(request.user)
    payments = Payment.objects.filter(organization=org).select_related(
        "invoice",
        "invoice__customer",
        "organization",
        "receipt",
    ).order_by("-payment_date", "-id")

    return render(
        request,
        "payments/payment_list.html",
        {
            "payments": payments
        },
    )


@login_required
def payment_create(request, invoice_id):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)
    invoice = get_object_or_404(Invoice, pk=invoice_id, organization=org)

    form = PaymentForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.organization = org
            payment.received_by = request.user
            payment.save()

            messages.success(request, "Payment recorded successfully.")

            ActivityLog.objects.create(
                user=request.user,
                action=f"Payment {payment.reference} (₦{payment.amount}) recorded for Invoice {invoice.invoice_no}"
            )

            return redirect("payment_detail", payment.pk)

    else:
        ref_code = f"TRX{datetime.now().strftime('%m%d%H%M%S')}"
        form = PaymentForm(initial={
            'amount': invoice.balance if invoice.balance > 0 else 0,
            'payment_date': date.today(),
            'reference': ref_code
        })

    return render(
        request,
        "payments/payment_form.html",
        {
            "form": form,
            "invoice": invoice,
        },
    )


@login_required
def payment_detail(request, pk):
    org = _get_user_organization(request.user)
    payment = get_object_or_404(
        Payment.objects.select_related(
            "invoice",
            "invoice__customer",
            "receipt",
            "organization",
        ),
        pk=pk,
        organization=org
    )

    return render(
        request,
        "payments/payment_detail.html",
        {
            "payment": payment,
            "invoice": payment.invoice,
            "organization": payment.organization or org
        },
    )


@login_required
def payment_update(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)
    from sales.payments.models import Payment as EnterprisePayment
    import uuid as uuid_lib

    is_valid_uuid = False
    try:
        uuid_lib.UUID(str(pk))
        is_valid_uuid = True
    except (ValueError, TypeError):
        pass

    payment = None
    if is_valid_uuid:
        payment = EnterprisePayment.objects.filter(organization=org, uuid=pk).first()
    elif str(pk).isdigit():
        payment = EnterprisePayment.objects.filter(organization=org, id=int(pk)).first()

    if not payment:
        payment = get_object_or_404(Payment, pk=pk, organization=org)

    form = PaymentForm(request.POST or None, instance=payment)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            if hasattr(payment, 'invoice') and payment.invoice:
                payment.invoice.update_status()
            messages.success(request, "Payment updated successfully.")
            return redirect("payment_detail", pk=payment.pk)

    return render(
        request,
        "payments/payment_form.html",
        {
            "form": form,
            "payment": payment,
            "invoice": getattr(payment, 'invoice', None),
            "is_edit": True,
        },
    )


@login_required
def payment_delete(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN'])
    org = _get_user_organization(request.user)
    from sales.payments.models import Payment as EnterprisePayment
    import uuid as uuid_lib

    is_valid_uuid = False
    try:
        uuid_lib.UUID(str(pk))
        is_valid_uuid = True
    except (ValueError, TypeError):
        pass

    payment = None
    if is_valid_uuid:
        payment = EnterprisePayment.objects.filter(organization=org, uuid=pk).first()
    elif str(pk).isdigit():
        payment = EnterprisePayment.objects.filter(organization=org, id=int(pk)).first()

    if not payment:
        payment = get_object_or_404(Payment, pk=pk, organization=org)

    if request.method == 'POST':
        invoice = getattr(payment, 'invoice', None)
        ref = getattr(payment, 'reference', getattr(payment, 'receipt_number', ''))
        payment.delete()
        if invoice:
            invoice.update_status()
        messages.success(request, "Payment deleted successfully.")
        ActivityLog.objects.create(
            user=request.user,
            action=f"Payment {ref} deleted"
        )
        return redirect("payment_list")

    return render(
        request,
        "payments/payment_confirm_delete.html",
        {
            "payment": payment,
            "invoice": payment.invoice,
        },
    )


def _build_receipt_context(receipt_obj):
    payment = receipt_obj.payment
    invoice = payment.invoice if payment else None
    customer = invoice.customer if invoice else None
    org = receipt_obj.organization or (invoice.organization if invoice else None)

    previously_paid = Decimal("0.00")
    invoice_total = Decimal("0.00")
    balance_remaining = Decimal("0.00")

    if invoice and payment:
        from invoices.models import Payment as LegacyPayment
        try:
            from sales.payments.models import Payment as SalesPayment
        except ImportError:
            SalesPayment = None

        invoice_total = invoice.effective_total_due
        all_payments = list(LegacyPayment.objects.filter(invoice_id=invoice.id))
        if SalesPayment:
            all_payments.extend(list(SalesPayment.objects.filter(invoice_id=invoice.id)))

        valid_payments = [
            p for p in all_payments
            if getattr(p, 'status', None) not in ('REVERSED', 'REFUNDED', 'FAILED')
        ]
        valid_payments.sort(key=lambda p: (
            getattr(p, 'payment_date', date.today()),
            p.pk if isinstance(p.pk, int) else str(p.pk)
        ))

        previously_paid = Decimal("0.00")
        for p in valid_payments:
            if str(p.pk) == str(payment.pk):
                break
            previously_paid += p.amount
        balance_remaining = max(Decimal("0.00"), invoice_total - (previously_paid + payment.amount))

    from core.documents.context_builder import DocumentContextBuilder
    return DocumentContextBuilder.build(
        receipt_obj,
        title=f"Receipt #{receipt_obj.receipt_no}",
        extra_context={
            "receipt": receipt_obj,
            "payment": payment,
            "invoice": invoice,
            "customer": customer,
            "organization": org,
            "date": payment.payment_date if payment else receipt_obj.issued_at,
            "doc_type": "PAYMENT RECEIPT",
            "invoice_total": invoice_total,
            "previously_paid": previously_paid,
            "balance_remaining": balance_remaining,
        }
    )


def _fetch_receipt(pk, org):
    try:
        return Receipt.objects.select_related(
            "payment",
            "payment__invoice",
            "payment__invoice__customer",
            "organization",
        ).get(
            Q(pk=pk) | Q(receipt_no=pk),
            Q(organization=org) | Q(payment__organization=org) | Q(payment__invoice__organization=org) | Q(organization__isnull=True)
        )
    except (Receipt.DoesNotExist, ValueError):
        try:
            from sales.payments.models import Receipt as SalesReceipt
            return SalesReceipt.objects.select_related(
                "payment",
                "payment__invoice",
                "payment__invoice__customer",
                "organization",
            ).get(
                Q(pk=pk) | Q(receipt_number=pk),
                Q(organization=org) | Q(payment__organization=org) | Q(payment__invoice__organization=org) | Q(organization__isnull=True)
            )
        except Exception:
            raise Http404("Receipt not found")


@login_required
def receipt_detail(request, pk):
    org = _get_user_organization(request.user)
    receipt = _fetch_receipt(pk, org)
    context = _build_receipt_context(receipt)
    return render(request, "documents/receipt/detail.html", context)


@login_required
def receipt_print(request, pk):
    org = _get_user_organization(request.user)
    receipt = _fetch_receipt(pk, org)
    context = _build_receipt_context(receipt)
    return render(request, "documents/receipt/detail.html", context)


@login_required
def receipt_pdf(request, pk):
    org = _get_user_organization(request.user)
    receipt = _fetch_receipt(pk, org)
    from django.template.loader import render_to_string
    context = _build_receipt_context(receipt)
    html_content = render_to_string("documents/receipt/detail.html", context, request=request)

    try:
        from weasyprint import HTML
        pdf_file = HTML(string=html_content).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="receipt-{receipt.receipt_no}.pdf"'
        return response
    except Exception:
        response = HttpResponse(html_content.encode('utf-8'), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="receipt-{receipt.receipt_no}.pdf"'
        return response


@login_required
def invoice_create(request):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)

    if request.method == 'POST':
        form = InvoiceForm(request.POST, organization=org)
        formset = InvoiceItemFormSet(request.POST, prefix='items', form_kwargs={'organization': org})

        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)
            invoice.organization = org
            items = formset.save(commit=False)

            from invoices.services import InvoiceService
            invoice = InvoiceService.create_invoice(invoice, items, user=request.user)
            return redirect('invoice_detail', invoice.id)

    else:
        form = InvoiceForm(organization=org)
        formset = InvoiceItemFormSet(prefix='items', form_kwargs={'organization': org})

    return render(
        request,
        'invoices/invoice_create.html',
        {
            'form': form,
            'formset': formset
        }
    )


@login_required
def invoice_update(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)
    invoice = get_object_or_404(Invoice, pk=pk, organization=org)

    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice, organization=org)
        formset = InvoiceItemFormSet(request.POST, instance=invoice, prefix='items', form_kwargs={'organization': org})

        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)
            invoice.organization = org
            items = formset.save(commit=False)

            from invoices.services import InvoiceService
            invoice = InvoiceService.update_invoice(invoice, items, user=request.user, deleted_items=formset.deleted_objects)

            messages.success(request, f"Invoice {invoice.invoice_no} updated successfully.")
            return redirect('invoice_detail', pk=invoice.pk)

    else:
        form = InvoiceForm(instance=invoice, organization=org)
        formset = InvoiceItemFormSet(instance=invoice, prefix='items', form_kwargs={'organization': org})

    return render(
        request,
        'sales/invoice/edit.html',
        {
            'form': form,
            'formset': formset,
            'invoice': invoice,
            'is_edit': True,
        }
    )


@login_required
def product_info(request, pk):
    organization = _get_user_organization(request.user)
    product = get_object_or_404(
        Product,
        pk=pk,
        organization=organization
    )
    return JsonResponse({
        "name": product.name,
        "description": product.description or product.name,
        "price": float(product.selling_price),
        "unit": product.unit,
    })


def _get_organization(invoice):
    return invoice.organization or Organization.objects.first()


@login_required
def invoice_print(request, pk):
    org = _get_user_organization(request.user)
    invoice = get_object_or_404(Invoice, id=pk, organization=org)
    organization = _get_organization(invoice)

    return render(
        request,
        'invoices/invoice_print.html',
        {
            'invoice': invoice,
            'organization': organization,
            'company': organization
        }
    )


@login_required
def invoice_pdf(request, pk):
    org = _get_user_organization(request.user)
    invoice = get_object_or_404(Invoice, id=pk, organization=org)
    organization = _get_organization(invoice)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{invoice.invoice_no}.pdf"'

    generate_invoice_pdf(response, invoice, organization)

    ActivityLog.objects.create(
        user=request.user,
        action=f"PDF Downloaded for Invoice {invoice.invoice_no}"
    )

    return response


@login_required
def invoice_send(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)
    invoice = get_object_or_404(Invoice, id=pk, organization=org)
    organization = _get_organization(invoice)

    buffer = io.BytesIO()
    generate_invoice_pdf(buffer, invoice, organization)
    pdf_content = buffer.getvalue()
    buffer.close()

    email = EmailMessage(
        subject=f"Invoice {invoice.invoice_no}",
        body=f"Dear {invoice.customer.company_name},\n\nPlease find attached invoice {invoice.invoice_no}.\n\nThank you for your business!",
        to=[invoice.customer.email]
    )

    email.attach(
        f"{invoice.invoice_no}.pdf",
        pdf_content,
        'application/pdf'
    )

    email.send()

    ActivityLog.objects.create(
        user=request.user,
        action=f"Invoice {invoice.invoice_no} Emailed"
    )

    return redirect('invoice_detail', pk=invoice.id)




@login_required
def customer_list(request):
    org = _get_user_organization(request.user)
    query = request.GET.get('q')

    customers = Customer.objects.filter(organization=org)

    if query:
        customers = customers.filter(company_name__icontains=query)

    return render(
        request,
        'invoices/customer_list.html',
        {
            'customers': customers,
            'query': query
        }
    )


@login_required
def customer_create(request):
    org = _get_user_organization(request.user)

    form = CustomerForm(request.POST or None)

    if form.is_valid():
        customer = form.save(commit=False)
        customer.organization = org
        customer.save()

        ActivityLog.objects.create(
            user=request.user,
            action=f"Customer {customer.company_name} Created"
        )

        return redirect('customer_list')

    return render(
        request,
        'invoices/customer_form.html',
        {
            'form': form
        }
    )


@login_required
def customer_update(request, pk):
    org = _get_user_organization(request.user)
    customer = get_object_or_404(Customer, pk=pk, organization=org)

    form = CustomerForm(request.POST or None, instance=customer)

    if form.is_valid():
        form.save()
        ActivityLog.objects.create(
            user=request.user,
            action=f"Customer {customer.company_name} Updated"
        )
        return redirect('customer_list')

    return render(
        request,
        'invoices/customer_form.html',
        {
            'form': form,
            'customer': customer
        }
    )


@login_required
def customer_delete(request, pk):
    org = _get_user_organization(request.user)
    customer = get_object_or_404(Customer, pk=pk, organization=org)

    if request.method == 'POST':
        company_name = customer.company_name
        customer.delete()
        ActivityLog.objects.create(
            user=request.user,
            action=f"Customer {company_name} Deleted"
        )
        return redirect('customer_list')

    return render(
        request,
        'invoices/customer_delete.html',
        {
            'customer': customer
        }
    )


@login_required
def customer_history(request, pk):
    org = _get_user_organization(request.user)
    customer = get_object_or_404(Customer, pk=pk, organization=org)

    invoices = Invoice.objects.filter(
        customer=customer,
        organization=org
    ).order_by('-invoice_date')

    return render(
        request,
        'invoices/customer_history.html',
        {
            'customer': customer,
            'invoices': invoices
        }
    )


@login_required
def customer_detail(request, pk):
    org = _get_user_organization(request.user)
    customer = get_object_or_404(Customer, pk=pk, organization=org)

    invoices = Invoice.objects.filter(customer=customer, organization=org)

    total_revenue = invoices.filter(
        status='PAID'
    ).aggregate(total=Sum('total_due'))['total'] or 0

    outstanding = invoices.filter(
        status='UNPAID'
    ).aggregate(total=Sum('total_due'))['total'] or 0

    context = {
        'customer': customer,
        'invoices': invoices.order_by('-id')[:10],
        'total_invoices': invoices.count(),
        'paid_invoices': invoices.filter(status='PAID').count(),
        'outstanding_invoices': invoices.filter(status='UNPAID').count(),
        'total_revenue': total_revenue,
        'outstanding': outstanding,
    }

    return render(
        request,
        'invoices/customer_detail.html',
        context
    )


# ==========================================
# PRODUCT CATEGORIES VIEWS
# ==========================================

@login_required
def category_list(request):
    org = _get_user_organization(request.user)
    categories = ProductCategory.objects.filter(organization=org)
    return render(
        request,
        "products/category_list.html",
        {"categories": categories}
    )


@login_required
def category_create(request):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)
    form = ProductCategoryForm(request.POST or None, organization=org)

    if request.method == 'POST':
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' created successfully.")
            return redirect("category_list")

    return render(
        request,
        "products/category_form.html",
        {"form": form}
    )


@login_required
def category_update(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)
    category = get_object_or_404(ProductCategory, pk=pk, organization=org)
    form = ProductCategoryForm(request.POST or None, instance=category, organization=org)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' updated successfully.")
            return redirect("category_list")

    return render(
        request,
        "products/category_form.html",
        {"form": form, "category": category, "is_edit": True}
    )


@login_required
def category_delete(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN'])
    org = _get_user_organization(request.user)
    category = get_object_or_404(ProductCategory, pk=pk, organization=org)

    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f"Category '{name}' deleted successfully.")
        return redirect("category_list")

    return render(
        request,
        "products/product_confirm_delete.html",
        {"object": category, "type": "Category"}
    )


# ==========================================
# PRODUCTS & SERVICES VIEWS
# ==========================================

@login_required
def product_list(request):

    organization = get_user_organization(request.user)

    products = Product.objects.filter(
        organization=organization
    )

    q = request.GET.get("q")

    if q:

        products = products.filter(

            Q(name__icontains=q) |

            Q(description__icontains=q) |

            Q(sku__icontains=q)

        )

    context = {

        "products": products,

        "total_products": products.count(),

        "services": products.filter(
            product_type="SERVICE"
        ).count(),

        "physical_products": products.filter(
            product_type="PRODUCT"
        ).count(),

        "active_products": products.filter(
            active=True
        ).count(),

    }

    return render(

        request,

        "products/product_list.html",

        context,

    )


@login_required
def product_create(request):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)
    form = ProductForm(request.POST or None, request.FILES or None, organization=org)

    if request.method == 'POST':
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product '{product.name}' created successfully.")
            return redirect("product_detail", product.pk)

    return render(
        request,
        "products/product_form.html",
        {"form": form}
    )


@login_required
def product_detail(request, pk):
    org = _get_user_organization(request.user)
    product = get_object_or_404(Product.objects.select_related('category'), pk=pk, organization=org)

    profit = (product.selling_price or 0) - (product.cost_price or 0)
    items = InvoiceItem.objects.filter(product=product).select_related('invoice', 'invoice__customer')
    invoices_count = items.values('invoice').distinct().count()
    revenue = items.aggregate(total=Sum('total'))['total'] or 0
    recent_invoices = Invoice.objects.filter(items__product=product).distinct().order_by('-created_at')[:5]

    context = {
        'product': product,
        'profit': profit,
        'invoices_count': invoices_count,
        'revenue': revenue,
        'recent_invoices': recent_invoices,
    }

    return render(
        request,
        "products/product_detail.html",
        context
    )


@login_required
def product_update(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)
    product = get_object_or_404(Product, pk=pk, organization=org)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product, organization=org)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, f"Product '{product.name}' updated successfully.")
            return redirect("product_detail", product.pk)

    return render(
        request,
        "products/product_form.html",
        {"form": form, "product": product, "is_edit": True}
    )


@login_required
def product_delete(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN'])
    org = _get_user_organization(request.user)
    product = get_object_or_404(Product, pk=pk, organization=org)

    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f"Product '{name}' deleted successfully.")
        return redirect("product_list")

    return render(
        request,
        "products/product_confirm_delete.html",
        {"object": product, "type": "Product"}
    )


@login_required
def quotation_list(request):
    org = _get_user_organization(request.user)
    status_filter = request.GET.get('status', 'all').upper()
    quotations = Quotation.objects.filter(organization=org).order_by('-id')

    if status_filter in ['DRAFT', 'SENT', 'APPROVED', 'REJECTED', 'EXPIRED', 'CONVERTED']:
        quotations = quotations.filter(status=status_filter)

    return render(
        request,
        'quotations/quotation_list.html',
        {
            'quotations': quotations,
            'current_status': status_filter
        }
    )


@login_required
def quotation_create(request):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)

    if request.method == 'POST':
        form = QuotationForm(request.POST, organization=org)
        formset = QuotationItemFormSet(request.POST, prefix='items', form_kwargs={'organization': org})

        if form.is_valid() and formset.is_valid():
            quotation = form.save(commit=False)
            quotation.organization = org
            items = formset.save(commit=False)

            from sales.services.quotation_service import QuotationService
            quotation = QuotationService.create(quotation, items, user=request.user)

            messages.success(request, f"Quotation {quotation.quotation_no} created successfully.")
            return redirect('quotation_detail', pk=quotation.pk)
        else:
            messages.error(request, "Unable to save quotation. Please check the highlighted errors below.")

    else:
        form = QuotationForm(organization=org)
        formset = QuotationItemFormSet(prefix='items', form_kwargs={'organization': org})

    return render(
        request,
        'quotations/quotation_form.html',
        {
            'form': form,
            'formset': formset,
            'is_edit': False
        }
    )


@login_required
def quotation_detail(request, pk):
    org = _get_user_organization(request.user)
    quotation = get_object_or_404(Quotation, pk=pk, organization=org)
    from core.documents.context_builder import DocumentContextBuilder
    context = DocumentContextBuilder.build(
        quotation,
        title=f"Quotation #{quotation.quotation_no}",
        extra_context={
            "customer": quotation.customer,
            "date": quotation.quotation_date,
            "valid_until": quotation.valid_until,
            "doc_type": "QUOTATION",
        }
    )
    return render(request, "documents/quotation/detail.html", context)


@login_required
def quotation_print(request, pk):
    org = _get_user_organization(request.user)
    quotation = get_object_or_404(Quotation, pk=pk, organization=org)
    return render(
        request,
        'quotations/quotation_print.html',
        {
            'quotation': quotation,
            'items': quotation.items.all(),
            'organization': org
        }
    )


@login_required
def quotation_convert(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)
    quotation = get_object_or_404(Quotation, pk=pk, organization=org)

    from sales.services.quotation_service import QuotationService
    invoice = QuotationService.convert_to_invoice(quotation, user=request.user)
    return redirect('invoice_detail', pk=invoice.id)

@login_required
def quotation_pdf(request, pk):
    org = _get_user_organization(request.user)
    quotation = get_object_or_404(Quotation, pk=pk, organization=org)
    from core.documents.context_builder import DocumentContextBuilder
    from django.template.loader import render_to_string
    context = DocumentContextBuilder.build(
        quotation,
        title=f"Quotation #{quotation.quotation_no}",
        extra_context={
            "customer": quotation.customer,
            "date": quotation.quotation_date,
            "valid_until": quotation.valid_until,
            "doc_type": "QUOTATION",
        }
    )
    html_content = render_to_string("documents/quotation/detail.html", context, request=request)
    
    try:
        from weasyprint import HTML
        pdf_file = HTML(string=html_content).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Quotation_{quotation.quotation_no}.pdf"'
        return response
    except Exception:
        response = HttpResponse(html_content.encode('utf-8'), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Quotation_{quotation.quotation_no}.pdf"'
        return response


@login_required
def quotation_send(request, pk):
    org = _get_user_organization(request.user)
    quotation = get_object_or_404(Quotation, pk=pk, organization=org)
    quotation.status = "SENT"
    quotation.save(update_fields=["status"])
    messages.success(request, f"Quotation {quotation.quotation_no} marked as sent to {quotation.customer.company_name}.")
    return redirect("quotation_detail", pk=quotation.pk)


@login_required
def quotation_delete(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN'])
    org = _get_user_organization(request.user)
    quotation = get_object_or_404(Quotation, pk=pk, organization=org)

    if request.method == 'POST':
        no = quotation.quotation_no
        quotation.delete()
        messages.success(request, f"Quotation {no} deleted successfully.")
        return redirect('quotation_list')

    return render(
        request,
        'products/product_confirm_delete.html',
        {'object': quotation, 'type': 'Quotation'}
    )


@login_required
@require_permission("quotation_template.view")
def quotation_template_list(request):
    org = _get_user_organization(request.user)
    service = QuotationTemplateService(organization=org)

    # Ensure organization has an initial default template seeded
    service.get_default_template()

    templates = service.get_templates(include_inactive=True)

    from .permissions import has_permission
    can_create = has_permission(request.user, "quotation_template.create", request=request)

    return render(
        request,
        "quotation_templates/list.html",
        {
            "templates": templates,
            "organization": org,
            "can_create": can_create,
        }
    )



@login_required
@require_permission("quotation_template.create")
def quotation_template_create(request):
    org = _get_user_organization(request.user)

    if request.method == "POST":
        form = QuotationTemplateForm(request.POST, organization=org)
        if form.is_valid():
            template = form.save()
            messages.success(request, f"Quotation template '{template.name}' created successfully.")
            return redirect("quotation_template_list")
    else:
        form = QuotationTemplateForm(organization=org)

    return render(
        request,
        "quotation_templates/form.html",
        {
            "form": form,
            "title": "New Quotation Template",
            "button_text": "Create Template",
        }
    )


@login_required
@require_permission("quotation_template.edit")
def quotation_template_edit(request, pk):
    org = _get_user_organization(request.user)
    template = get_object_or_404(QuotationTemplate, pk=pk, organization=org)

    if request.method == "POST":
        form = QuotationTemplateForm(request.POST, instance=template, organization=org)
        if form.is_valid():
            template = form.save()
            messages.success(request, f"Quotation template '{template.name}' updated successfully.")
            return redirect("quotation_template_list")
    else:
        form = QuotationTemplateForm(instance=template, organization=org)

    return render(
        request,
        "quotation_templates/form.html",
        {
            "form": form,
            "template": template,
            "title": f"Edit Template — {template.name}",
            "button_text": "Save Changes",
        }
    )


@login_required
@require_permission("quotation_template.set_default")
def quotation_template_set_default(request, pk):
    org = _get_user_organization(request.user)
    template = get_object_or_404(QuotationTemplate, pk=pk, organization=org)

    if not template.is_active:
        messages.error(request, "An inactive template cannot be designated as default.")
        return redirect("quotation_template_list")

    service = QuotationTemplateService(organization=org)
    service.set_default_template(template.id)

    messages.success(request, f"'{template.name}' is now the default quotation template for {org.name}.")
    return redirect("quotation_template_list")


@login_required
@require_permission("quotation_template.edit")
def quotation_template_toggle_active(request, pk):
    org = _get_user_organization(request.user)
    template = get_object_or_404(QuotationTemplate, pk=pk, organization=org)

    if template.is_default and template.is_active:
        messages.error(request, "Cannot deactivate the active default template. Designate another active template as default first.")
        return redirect("quotation_template_list")

    template.is_active = not template.is_active
    template.save(update_fields=["is_active", "updated_at"])

    status_str = "activated" if template.is_active else "deactivated"
    messages.success(request, f"Quotation template '{template.name}' has been {status_str}.")
    return redirect("quotation_template_list")


@login_required
@require_permission("quotation_template.delete")
def quotation_template_delete(request, pk):
    org = _get_user_organization(request.user)
    template = get_object_or_404(QuotationTemplate, pk=pk, organization=org)

    if template.is_default:
        messages.error(request, "Cannot delete the default template. Set another template as default before deleting.")
        return redirect("quotation_template_list")

    if request.method == "POST":
        name = template.name
        template.delete()
        messages.success(request, f"Quotation template '{name}' deleted successfully.")
        return redirect("quotation_template_list")

    return render(
        request,
        "quotation_templates/confirm_delete.html",
        {
            "template": template,
        }
    )


@login_required
def quotation_template_preview(request, pk):
    from .permissions import has_permission
    if not (has_permission(request.user, "quotation_template.view", request=request) or has_permission(request.user, "quotation.view", request=request)):
        raise PermissionDenied("You do not have permission to view quotation previews.")

    org = _get_user_organization(request.user)
    template = get_object_or_404(QuotationTemplate, pk=pk, organization=org)

    quotation_id = request.GET.get('quotation')
    if quotation_id:
        quotation = get_object_or_404(Quotation, pk=quotation_id, organization=org)
    else:
        quotation = QuotationTemplateService.get_demo_quotation_data(org)

    all_templates = QuotationTemplate.objects.filter(organization=org, is_active=True)
    all_quotations = Quotation.objects.filter(organization=org).order_by('-created_at')[:20]

    from .services.template_renderer import QuotationTemplateRenderer
    renderer = QuotationTemplateRenderer(organization=org)
    context = renderer.render_context(
        quotation=quotation,
        template=template,
        all_templates=all_templates,
        all_quotations=all_quotations
    )

    style = template.style if hasattr(template, 'style') else 'modern'
    template_name = QuotationTemplateRenderer.STYLE_TEMPLATE_MAP.get(style, QuotationTemplateRenderer.STYLE_TEMPLATE_MAP['modern'])

    return render(request, template_name, context)


