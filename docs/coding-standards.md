# Coding Standards & Guidelines

## Python & Django Standards
- Use PEP 8 guidelines for formatting.
- Always scope database queries by the active `Organization` (`organization=org`).
- Prefer service layer methods (`sales/services/`) over putting complex calculation logic in models or views.
- Keep unit tests updated in `tests.py`.

## HTML & CSS Standards
- Prefix all reusable CSS classes with `abs-` (`abs-card`, `abs-btn`, `abs-input`).
- Use CSS design token variables defined in `variables.css`.
- Use template components in `templates/components/` rather than repeating card or form HTML blocks.
