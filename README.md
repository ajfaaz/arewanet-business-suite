# ABS ERP (ArewaNet Business Suite)

An enterprise resource planning (ERP) platform built with Django. Designed for multi-tenant business operations, billing automation, financial management, and API integrations.

---

## 🚀 Modules

- ✓ **Authentication**: Role-based access control (Owner, Admin, Accountant, Sales, Staff) and JWT authentication.
- ✓ **Organizations**: Multi-tenant workspace isolation.
- ✓ **Customers**: Customer directory, profile management, and 360° customer financial summary.
- ✓ **Products & Categories**: Product catalog, inventory item classification, and pricing control.
- ✓ **Quotations**: Proposal builder with 1-click conversion to standard invoices.
- ✓ **Invoices**: Automated invoicing engine with tax/discount calculation, partial payments, and PDF generation.
- ✓ **Enterprise Payments**: Multi-channel payment recording (Cash, Bank Transfer, POS, Cheque, Online, Mobile Money) with receipt generation.
- ✓ **Receipts**: Auto-generated branded payment receipts.
- ✓ **Financial Documents**: Credit Notes, Debit Notes, Account Statements, and Aging Reports.
- ✓ **Subscriptions & Recurring Billing**: SaaS billing engine, billing cycles (`WEEKLY`, `MONTHLY`, `QUARTERLY`, `SEMI_ANNUAL`, `ANNUAL`), automated invoice generator command (`python manage.py generate_recurring_invoices`), MRR/ARR metrics, and 3-month revenue forecasting.
- ✓ **Enterprise REST API (`/api/v1/`)**: Complete REST API, OpenAPI 3.0 schema generation, and interactive Swagger UI / ReDoc documentation.
- ✓ **Reports & Analytics**: Sales reports, customer aging reports, revenue analytics, and executive dashboards.

---

## 🛠️ Tech Stack

- **Backend**: Python, Django 5, Django REST Framework, SimpleJWT
- **API Documentation**: OpenAPI 3.0, `drf-spectacular`, Swagger UI, ReDoc
- **PDF Engine**: ReportLab Document Engine
- **Frontend / Styling**: HTML5, Vanilla CSS / Bootstrap 5, JavaScript, ABS Design System
- **Database**: SQLite (Development), PostgreSQL (Production)

---

## 📋 Interactive API Documentation

Once the server is running (`python manage.py runserver`), access the interactive API endpoints:
- **Swagger UI**: [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)
- **ReDoc**: [http://127.0.0.1:8000/api/redoc/](http://127.0.0.1:8000/api/redoc/)
- **OpenAPI Schema**: [http://127.0.0.1:8000/api/schema/](http://127.0.0.1:8000/api/schema/)

---

## ⚙️ Quick Start

```bash
# Clone the repository
git clone https://github.com/ajfaaz/arewanet-business-suite.git

# Navigate to project root
cd arewanet-business-suite

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Run automated test suite
python manage.py test api sales invoices

# Start local server
python manage.py runserver
```

---

## 🔮 Upcoming Modules

- 📦 Inventory & Warehouse Management
- 🛒 Procurement & Purchase Orders
- 💰 General Ledger & Core Finance
- 👥 Human Resources (HR) & Payroll
- 📊 Advanced BI Analytics
- 📱 Flutter Mobile App (iOS & Android)

---

## 🏢 Developed by

Developed by **ArewaNet Ventures** — Enterprise Software Solutions.