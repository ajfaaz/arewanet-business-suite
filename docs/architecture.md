# Architecture Guidelines - ArewaNet Business Suite

## System Overview
ArewaNet Business Suite is a multi-tenant enterprise resource planning (ERP) system built on Django.

## Domain Model Inheritance Structure
```
BaseDocument (Abstract)
├── Invoice
└── Quotation

BaseLineItem (Abstract)
├── InvoiceItem
└── QuotationItem

Supporting Models:
- Payment
- ActivityLog
- Customer
- Product / ProductCategory
- Organization
```

## Layered Architecture
1. **Presentation Layer**: Django templates utilizing ABS Design System (`abs-card`, `abs-btn`, `abs-input`).
2. **Controller Layer**: Django view functions with login requirements and multi-tenant organization scoping (`_get_user_organization`).
3. **Service Layer** (`sales/services/`): Pure Python domain logic (`DocumentNumberService`, `InvoiceCalculator`, `ExportService`).
4. **Data Access Layer**: Django ORM models inheriting from `BaseDocument` and `BaseLineItem`.
