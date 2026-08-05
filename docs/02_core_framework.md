# 02. ABS Core Framework Reference

## Core Abstract Models (`core/models.py`)
- `TimeStampedModel`: Provides `created_at` and `updated_at`.
- `UUIDModel`: Provides unique `uuid`.
- `SoftDeleteModel`: Provides `is_deleted` and `deleted_at`.
- `ActiveModel`: Provides `is_active`.
- `AuditModel`: Provides `created_by` and `updated_by` ForeignKeys.

## Core Choices (`core/choices.py`)
- `InvoiceStatus`: `DRAFT`, `UNPAID`, `PARTIAL`, `PAID`, `OVERDUE`, `CANCELLED`.
- `PaymentMethod`: `BANK`, `CASH`, `POS`, `CHEQUE`, `PAYSTACK`, `FLUTTERWAVE`.
- `ProductType`: `GOODS`, `SERVICE`.

## Core Utilities (`core/utils.py`)
- `generate_invoice_number(prefix)`
- `generate_reference(prefix)`
- `format_currency(amount, currency)`
- `format_phone(phone)`
