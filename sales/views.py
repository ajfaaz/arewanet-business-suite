from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.core.exceptions import PermissionDenied, ValidationError

from invoices.views import _get_user_organization, _check_permission
from invoices.models import Customer, Invoice
from sales.models import CreditNote, DebitNote
from sales.forms import CreditNoteForm, DebitNoteForm
from sales.selectors import CreditSelector, StatementSelector, AgingSelector
from sales.services import CreditNoteService, DebitNoteService, StatementService, AgingService
from core.documents.pdf_service import PDFService


# --- CREDIT NOTES VIEWS ---

@login_required
def credit_note_list(request):
    org = _get_user_organization(request.user)
    query = request.GET.get('q', '')
    status = request.GET.get('status', '')
    customer_id = request.GET.get('customer', '')

    credit_notes = CreditSelector.get_credit_notes(
        organization=org,
        query=query,
        customer_id=customer_id,
        status=status
    )

    customers = Customer.objects.filter(organization=org).order_by('company_name')

    return render(request, 'sales/credit_notes/list.html', {
        'credit_notes': credit_notes,
        'search_query': query,
        'selected_status': status,
        'selected_customer': customer_id,
        'customers': customers,
    })


@login_required
def credit_note_create(request, invoice_id=None):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)

    initial = {}
    invoice = None
    if invoice_id:
        invoice = get_object_or_404(Invoice, pk=invoice_id, organization=org)
        initial['invoice'] = invoice.pk

    form = CreditNoteForm(request.POST or None, organization=org, initial=initial)

    if request.method == 'POST':
        if form.is_valid():
            try:
                inv = form.cleaned_data['invoice']
                amt = form.cleaned_data['amount']
                reason = form.cleaned_data['reason']

                cn = CreditNoteService.issue_credit_note(
                    organization=org,
                    invoice=inv,
                    amount=amt,
                    reason=reason,
                    user=request.user
                )

                messages.success(request, f"Credit Note {cn.credit_note_no} issued successfully.")
                return redirect('credit_note_detail', pk=cn.pk)
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))

    return render(request, 'sales/credit_notes/create.html', {
        'form': form,
        'invoice': invoice,
    })


@login_required
def credit_note_detail(request, pk):
    org = _get_user_organization(request.user)
    credit_note = get_object_or_404(CreditNote, pk=pk, organization=org)

    return render(request, 'sales/credit_notes/detail.html', {
        'credit_note': credit_note,
        'organization': org,
        'invoice': credit_note.invoice,
        'customer': credit_note.customer,
    })


@login_required
def credit_note_pdf(request, pk):
    org = _get_user_organization(request.user)
    credit_note = get_object_or_404(CreditNote, pk=pk, organization=org)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{credit_note.credit_note_no}.pdf"'

    PDFService.generate_credit_note(credit_note, response)
    return response


@login_required
def credit_note_cancel(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN'])
    org = _get_user_organization(request.user)
    credit_note = get_object_or_404(CreditNote, pk=pk, organization=org)

    if request.method == 'POST':
        CreditNoteService.cancel_credit_note(credit_note, user=request.user)
        messages.success(request, f"Credit Note {credit_note.credit_note_no} cancelled.")
        return redirect('credit_note_detail', pk=credit_note.pk)

    return render(request, 'sales/credit_notes/confirm_cancel.html', {
        'credit_note': credit_note,
    })


# --- DEBIT NOTES VIEWS ---

@login_required
def debit_note_list(request):
    org = _get_user_organization(request.user)
    query = request.GET.get('q', '')
    status = request.GET.get('status', '')
    customer_id = request.GET.get('customer', '')

    debit_notes = CreditSelector.get_debit_notes(
        organization=org,
        query=query,
        customer_id=customer_id,
        status=status
    )

    customers = Customer.objects.filter(organization=org).order_by('company_name')

    return render(request, 'sales/debit_notes/list.html', {
        'debit_notes': debit_notes,
        'search_query': query,
        'selected_status': status,
        'selected_customer': customer_id,
        'customers': customers,
    })


@login_required
def debit_note_create(request, invoice_id=None):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)

    initial = {}
    invoice = None
    if invoice_id:
        invoice = get_object_or_404(Invoice, pk=invoice_id, organization=org)
        initial['invoice'] = invoice.pk

    form = DebitNoteForm(request.POST or None, organization=org, initial=initial)

    if request.method == 'POST':
        if form.is_valid():
            try:
                inv = form.cleaned_data['invoice']
                amt = form.cleaned_data['amount']
                reason = form.cleaned_data['reason']

                dn = DebitNoteService.issue_debit_note(
                    organization=org,
                    invoice=inv,
                    amount=amt,
                    reason=reason,
                    user=request.user
                )

                messages.success(request, f"Debit Note {dn.debit_note_no} issued successfully.")
                return redirect('debit_note_detail', pk=dn.pk)
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))

    return render(request, 'sales/debit_notes/create.html', {
        'form': form,
        'invoice': invoice,
    })


@login_required
def debit_note_detail(request, pk):
    org = _get_user_organization(request.user)
    debit_note = get_object_or_404(DebitNote, pk=pk, organization=org)

    return render(request, 'sales/debit_notes/detail.html', {
        'debit_note': debit_note,
        'organization': org,
        'invoice': debit_note.invoice,
        'customer': debit_note.customer,
    })


@login_required
def debit_note_pdf(request, pk):
    org = _get_user_organization(request.user)
    debit_note = get_object_or_404(DebitNote, pk=pk, organization=org)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{debit_note.debit_note_no}.pdf"'

    PDFService.generate_debit_note(debit_note, response)
    return response


@login_required
def debit_note_cancel(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN'])
    org = _get_user_organization(request.user)
    debit_note = get_object_or_404(DebitNote, pk=pk, organization=org)

    if request.method == 'POST':
        DebitNoteService.cancel_debit_note(debit_note, user=request.user)
        messages.success(request, f"Debit Note {debit_note.debit_note_no} cancelled.")
        return redirect('debit_note_detail', pk=debit_note.pk)

    return render(request, 'sales/debit_notes/confirm_cancel.html', {
        'debit_note': debit_note,
    })


# --- STATEMENTS & AGING VIEWS ---

@login_required
def customer_statement_view(request, customer_id):
    org = _get_user_organization(request.user)
    customer = get_object_or_404(Customer, pk=customer_id, organization=org)

    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    statement_data = StatementSelector.get_statement_context(
        customer=customer,
        start_date=start_date,
        end_date=end_date
    )

    return render(request, 'sales/statements/customer_statement.html', {
        'statement': statement_data,
        'customer': customer,
        'organization': org,
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required
def customer_statement_pdf(request, customer_id):
    org = _get_user_organization(request.user)
    customer = get_object_or_404(Customer, pk=customer_id, organization=org)

    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    statement_data = StatementSelector.get_statement_context(
        customer=customer,
        start_date=start_date,
        end_date=end_date
    )

    response = HttpResponse(content_type='application/pdf')
    filename = f"Statement_{customer.company_name.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    PDFService.generate_statement(statement_data, response)
    return response


@login_required
def aging_report_view(request):
    org = _get_user_organization(request.user)
    aging_data = AgingSelector.get_aging_report(organization=org)

    return render(request, 'sales/statements/aging_report.html', {
        'aging': aging_data,
        'organization': org,
    })
