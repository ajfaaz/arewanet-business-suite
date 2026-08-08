# ABS ERP — Architecture & Design Specification

This document details the architectural principles, domain modeling, request lifecycle, permission boundaries, and API versioning strategy of the ABS Enterprise Resource Planning (ERP) platform.

---

## 1. High-Level Architecture Overview

ABS ERP follows a clean, modular, multi-tenant 5-layer backend pattern to ensure strict separation of concerns, maintainability, and testability.

```
┌─────────────────────────────────────────────────────────────┐
│                    HTTP Request (REST / JWT)                 │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. API View Layer (views.py / ViewSets)                      │
│    - Routing, Authentication, Request Parsing               │
│    - Standard API Response formatting                       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Serializer Layer (serializers.py)                        │
│    - Input validation & Schema representation               │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Service Layer (services.py)                              │
│    - Business rules, state transitions, domain exceptions    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Selector Layer (selectors.py)                            │
│    - Optimized DB queries, select_related & prefetch_related │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Model & Data Layer (models.py / DB)                       │
│    - Model definitions, composite indexes, ORM mapping       │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Multi-Tenant Domain Hierarchy

Every entity in ABS ERP belongs to an `Organization`. Multi-tenancy is enforced at both the database and access control layers.

```
                      Organization
                           │
    ┌──────────┬───────────┼───────────┬──────────┐
    ▼          ▼           ▼           ▼          ▼
Customers   Products   Quotations   Invoices   Payments
    │          │           │           │          │
    └──────────┴───────────┼───────────┴──────────┘
                           ▼
                  Financial Documents
             (Receipts, Statements, PDFs)
```

---

## 3. Base Service & Selector Design

### Base Service (`core/services/base.py`)
All domain services inherit from `BaseService`, providing standard CRUD primitives while keeping custom business logic in domain-specific services:

```python
class BaseService:
    @staticmethod
    def create(model, **kwargs):
        return model.objects.create(**kwargs)

    @staticmethod
    def update(instance, **kwargs):
        for key, value in kwargs.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    @staticmethod
    def delete(instance):
        instance.delete()
```

### Base Selector (`core/selectors/base.py`)
All data retrieval selectors inherit from `BaseSelector` to enforce organization filtering and query optimization:

```python
class BaseSelector:
    @staticmethod
    def list(queryset):
        return queryset
```

---

## 4. Multi-Tenant Security & Permissions

Access control is managed centralizing organization membership and domain permissions:

- **`IsOrganizationMember`** (`core/permissions/organization.py`):
  Ensures that requests are granted only to authenticated users attached to an active organization. Any request attempt targeting another organization's record returns `404 Not Found` (preventing data leakage).
- **`IsOrganizationAdmin`**:
  Restricts administrative operations (e.g., organization settings, billing) to admin users.
- **Domain Role Permissions** (`core/permissions/roles.py`):
  Fine-grained permissions (`CanManageCustomers`, `CanManageProducts`, `CanManageInvoices`, `CanManagePayments`).

---

## 5. API Exception Handling & Unified Response Contract

All REST APIs return a consistent JSON schema:

### Success Response Format
```json
{
  "success": true,
  "message": "Invoices retrieved successfully.",
  "data": [...],
  "pagination": {
    "count": 45,
    "next": "http://.../api/v1/invoices/?page=2",
    "previous": null
  }
}
```

### Error Response Format (`core/api/exceptions.py`)
```json
{
  "success": false,
  "message": "Payment exceeds invoice balance due.",
  "code": "PAYMENT_EXCEEDS_BALANCE",
  "errors": {}
}
```

Raw tracebacks are never exposed to clients.

---

## 6. API Versioning Policy

ABS ERP strictly enforces URL-path versioning:

- **Current Version**: `/api/v1/`
  - Used by Web Dashboard, Mobile Applications (Flutter), and External Integrations.
- **Backward Compatibility Guarantee**:
  - Existing `/api/v1/` endpoints remain stable without breaking signature changes.
- **Future Major Releases**:
  - Breaking schema or contract changes will be published under `/api/v2/`, allowing legacy clients to function smoothly.
