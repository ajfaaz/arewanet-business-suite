# 04. Coding Standards

## Python & Django
- Keep views thin; delegate multi-step writes to domain services.
- Wrap write transactions in `@transaction.atomic`.
- Inherit core model mixins (`TimeStampedModel`, `UUIDModel`, `AuditModel`).

## HTML & CSS
- Prefix reusable CSS rules with `abs-`.
- Avoid hardcoded color values; use CSS variables from `variables.css`.
