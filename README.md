# ABS ERP — Modular Multi-Tenant Enterprise Resource Planning System

**ABS ERP** is a modular, multi-tenant business management platform designed to help organizations manage customers, products, quotations, invoices, payments, financial documents, and business analytics from a unified system.

---

## 🚀 Key Features

### 🏢 Sales & Financial Management
- **Multi-Tenancy**: Organization-level data isolation across all modules and APIs.
- **Customer Directory**: Manage enterprise customer profiles, contact info, and real-time outstanding balances.
- **Product & Category Management**: Dynamic catalog, SKU tracking, pricing, and active status.
- **Quotation Workflow**: Create quotes, auto-calculate totals, approve/reject, and converts to invoices in 1 click.
- **Invoice Processing**: Generate invoices, track payment status (`UNPAID`, `PARTIALLY_PAID`, `PAID`, `OVERDUE`), calculate balance due, and issue debit/credit notes.
- **Payments & Receipts**: Record payments (Bank Transfer, Cash, Card, Cheque), handle allocations, auto-update invoice balances, and generate printable PDF receipts.
- **Financial Documents**: Real-time Customer Account Statements and PDF invoice generation.
- **Analytics & Dashboard**: Read-only aggregated analytics API powering Web and Flutter dashboards.

### 🛡️ Enterprise Foundation
- **JWT Authentication**: Secure token authentication with access and refresh tokens.
- **Role & Permission Engine**: Multi-tenant membership checks (`IsOrganizationMember`) and granular domain access permissions (`CanManageInvoices`, etc.).
- **Standardized API Contract**: Predictable JSON responses (`success`, `message`, `data`, `pagination`, `errors`).
- **Domain Business Exceptions**: Domain exceptions with custom error codes (`INVOICE_ALREADY_PAID`, `PAYMENT_EXCEEDS_BALANCE`, `INVALID_QUOTATION_STATUS`).
- **Database Query Optimization**: Optimized selectors with `select_related`/`prefetch_related` and composite DB indexes.
- **Comprehensive Test Suite**: Automated unit and end-to-end integration tests.

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Backend Framework** | Python 3.12, Django 6.0 |
| **API Architecture** | Django REST Framework, JWT (`djangorestframework_simplejwt`), `django-filter` |
| **API Docs & Schema** | OpenAPI 3.0, `drf-spectacular` (Swagger UI & ReDoc) |
| **Database** | SQLite (Development), PostgreSQL (Production) |
| **PDF Generation** | ReportLab |
| **Frontend** | Django Templates, HTML5, Vanilla CSS, JavaScript |

---

## 📂 Project Structure

```
arewanet_invoice/
│
├── manage.py
├── arewanet_invoice/         # Core project settings & root URLs
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── core/                     # Enterprise foundation framework
│   ├── api/                  # OrganizationModelViewSet & Exception Handlers
│   ├── exceptions/           # Domain business exceptions
│   ├── permissions/          # Multi-tenant & role permissions
│   ├── services/             # BaseService primitives
│   ├── selectors/            # BaseSelector primitives
│   └── pagination.py         # StandardPagination engine
│
├── api/                      # REST API Module
│   ├── authentication/
│   ├── customers/
│   ├── products/
│   ├── quotations/
│   ├── invoices/
│   ├── payments/
│   ├── dashboard/
│   └── views/
│
├── invoices/                 # Core Sales & Invoice Django App
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   └── services/
│
├── sales/                    # Payments, Credit/Debit Notes & Statements
│   ├── payments/
│   ├── services/
│   └── templates/
│
├── docs/                     # Technical & Architectural Documentation
│   ├── architecture.md
│   ├── production-checklist.md
│   └── backup-guide.md
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## ⚙️ Developer Setup Guide

### 1. Prerequisites
- Python 3.10+
- Git

### 2. Clone & Virtual Environment Setup
```bash
git clone <repository_url>
cd arewanet_invoice

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Activate virtual environment (Linux/macOS)
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
copy .env.example .env     # Windows
cp .env.example .env       # Linux/macOS
```

### 5. Run Database Migrations & Create Superuser
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Start Development Server
```bash
python manage.py runserver
```
Visit http://127.0.0.1:8000 in your browser.

---

## 🧪 Running Automated Tests

Run the full automated unit, security, and performance test suite:

```bash
python manage.py test core api sales invoices
```

---

## 📖 API Documentation & Endpoints

ABS ERP features interactive OpenAPI 3.0 documentation:

- **Swagger UI**: [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)
- **ReDoc**: [http://127.0.0.1:8000/api/redoc/](http://127.0.0.1:8000/api/redoc/)
- **OpenAPI Schema**: [http://127.0.0.1:8000/api/schema/](http://127.0.0.1:8000/api/schema/)
- **API Health Check**: `GET /api/v1/health/`

---

## 🗺️ Roadmap & Phase Progression

- **✅ Phase 1 — Sales Module & Enterprise Foundation (v1.0.0-beta)**: Complete core sales lifecycle, multi-tenancy, REST API, pagination, filtering, query optimization, security, and test suite.
- **🚀 Phase 2 — Inventory & Warehouse Management**: Warehouses, Stock Ledger, Goods Received Notes (GRN), Goods Issue Notes (GIN), Stock Transfers, Serial Numbers, Valuation (FIFO / Weighted Average).
- **🛒 Phase 3 — Procurement**: Suppliers, Purchase Orders, Goods Receipts, Supplier Invoices.
- **💰 Phase 4 — General Ledger & Financial Accounting**: Chart of Accounts, Journal Entries, Bank Reconciliation.