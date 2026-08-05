# 01. Project Architecture - ArewaNet Business Suite

## Architecture Overview
The ArewaNet Business Suite (ABS) follows a modular, domain-driven Django architecture.

```
arewanet_business_suite/
├── core/             # Shared framework (Base models, choices, constants, managers)
├── invoices/         # Legacy Invoice & Customer models
├── sales/            # Sales domain services, BaseDocument abstract domain models
├── static/           # ABS Design System v1.0 CSS, JS, SVG assets
└── templates/        # Component template library & Sales pages
```

## Layer Responsibilities
1. **Models**: Domain data structures inheriting from `TimeStampedModel`, `UUIDModel`, `AuditModel`.
2. **Services**: Pure Python business logic and atomic database transactions (`@transaction.atomic`).
3. **Views**: Thin HTTP controllers validating forms and delegating domain operations to services.
4. **Templates**: Reusable UI components from `templates/components/`.
