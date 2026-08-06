from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.exceptions import ValidationError

from invoices.views import _get_user_organization, _check_permission
from invoices.models import Customer
from sales.subscriptions.models import (
    Subscription,
    SubscriptionTemplate,
    SubscriptionItem
)
from sales.subscriptions.forms import (
    SubscriptionForm,
    SubscriptionTemplateForm,
    SubscriptionItemFormSet
)
from sales.subscriptions.services import SubscriptionService
from sales.subscriptions.selectors import SubscriptionSelector
from core.choices import SubscriptionStatus, BillingCycle


@login_required
def subscription_list(request):
    org = _get_user_organization(request.user)
    query = request.GET.get('q', '')
    status = request.GET.get('status', '')
    customer_id = request.GET.get('customer', '')

    subscriptions = SubscriptionSelector.get_subscriptions(
        organization=org,
        query=query,
        customer_id=customer_id,
        status=status
    )
    customers = Customer.objects.filter(organization=org).order_by('company_name')

    metrics = SubscriptionService.calculate_mrr_arr(org)

    return render(request, 'subscriptions/list.html', {
        'subscriptions': subscriptions,
        'search_query': query,
        'selected_status': status,
        'selected_customer': customer_id,
        'customers': customers,
        'metrics': metrics,
    })


@login_required
def subscription_create(request):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)

    form = SubscriptionForm(request.POST or None, organization=org)
    formset = SubscriptionItemFormSet(request.POST or None)

    template_id = request.GET.get('template')
    if template_id and not request.POST:
        tmpl = get_object_or_404(SubscriptionTemplate, pk=template_id, organization=org)
        form.initial.update({
            'title': tmpl.title,
            'billing_cycle': tmpl.billing_cycle,
            'notes': tmpl.description,
            'template': tmpl.pk
        })

    if request.method == 'POST':
        if form.is_valid() and formset.is_valid():
            try:
                sub = form.save(commit=False)
                sub.organization = org
                sub.created_by = request.user

                # Set next_invoice_date
                sub.next_invoice_date = sub.start_date
                sub.save()

                formset.instance = sub
                formset.save()

                messages.success(request, f"Subscription '{sub.title}' created successfully.")
                return redirect('subscription_detail', pk=sub.pk)
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))

    return render(request, 'subscriptions/create.html', {
        'form': form,
        'formset': formset,
        'organization': org,
    })


@login_required
def subscription_detail(request, pk):
    org = _get_user_organization(request.user)
    subscription = get_object_or_404(
        Subscription.objects.select_related('customer', 'template', 'created_by').prefetch_related('items', 'logs'),
        pk=pk,
        organization=org
    )

    # Invoices generated for this subscription
    generated_invoices = subscription.customer.invoice_set.filter(
        project_name__icontains=f"Recurring: {subscription.title}"
    ).order_by('-created_at')

    return render(request, 'subscriptions/detail.html', {
        'subscription': subscription,
        'items': subscription.items.all(),
        'logs': subscription.logs.all(),
        'generated_invoices': generated_invoices,
    })


@login_required
def subscription_pause(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)
    subscription = get_object_or_404(Subscription, pk=pk, organization=org)

    if request.method == 'POST':
        SubscriptionService.pause(subscription, user=request.user)
        messages.success(request, f"Subscription '{subscription.title}' paused.")

    return redirect('subscription_detail', pk=subscription.pk)


@login_required
def subscription_resume(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)
    subscription = get_object_or_404(Subscription, pk=pk, organization=org)

    if request.method == 'POST':
        SubscriptionService.resume(subscription, user=request.user)
        messages.success(request, f"Subscription '{subscription.title}' resumed.")

    return redirect('subscription_detail', pk=subscription.pk)


@login_required
def subscription_cancel(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN'])
    org = _get_user_organization(request.user)
    subscription = get_object_or_404(Subscription, pk=pk, organization=org)

    if request.method == 'POST':
        SubscriptionService.cancel(subscription, user=request.user)
        messages.success(request, f"Subscription '{subscription.title}' cancelled.")

    return redirect('subscription_detail', pk=subscription.pk)


@login_required
def subscription_generate_invoice(request, pk):
    _check_permission(request.user, ['OWNER', 'ADMIN', 'ACCOUNTANT'])
    org = _get_user_organization(request.user)
    subscription = get_object_or_404(Subscription, pk=pk, organization=org)

    if request.method == 'POST':
        try:
            inv = SubscriptionService.generate_invoice(subscription, user=request.user)
            messages.success(request, f"Invoice #{inv.invoice_no} generated successfully.")
            return redirect('invoice_detail', pk=inv.pk)
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))

    return redirect('subscription_detail', pk=subscription.pk)


@login_required
def subscription_dashboard(request):
    org = _get_user_organization(request.user)
    metrics = SubscriptionService.calculate_mrr_arr(org)
    forecast = SubscriptionSelector.get_revenue_forecast(org, months=3)
    recent_subscriptions = SubscriptionSelector.get_subscriptions(org)[:10]

    return render(request, 'subscriptions/dashboard.html', {
        'metrics': metrics,
        'forecast': forecast,
        'recent_subscriptions': recent_subscriptions,
    })


@login_required
def subscription_forecast(request):
    org = _get_user_organization(request.user)
    months = int(request.GET.get('months', 6))
    forecast = SubscriptionSelector.get_revenue_forecast(org, months=months)
    metrics = SubscriptionService.calculate_mrr_arr(org)

    return render(request, 'subscriptions/forecast.html', {
        'forecast': forecast,
        'metrics': metrics,
        'months': months,
    })


@login_required
def template_list(request):
    org = _get_user_organization(request.user)
    templates = SubscriptionSelector.get_templates(org)

    return render(request, 'subscriptions/templates_list.html', {
        'templates': templates,
    })


@login_required
def template_create(request):
    _check_permission(request.user, ['OWNER', 'ADMIN'])
    org = _get_user_organization(request.user)

    form = SubscriptionTemplateForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            tmpl = form.save(commit=False)
            tmpl.organization = org
            tmpl.created_by = request.user
            tmpl.save()

            messages.success(request, f"Template '{tmpl.title}' created.")
            return redirect('template_list')

    return render(request, 'subscriptions/template_create.html', {
        'form': form,
    })
