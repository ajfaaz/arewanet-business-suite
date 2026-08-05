# ABS Design System v1.0

## Purpose
ABS Design System provides reusable UI components, design tokens, and CSS architecture for all ArewaNet products.

## Design Principles
- **Consistency**: Unified typography, spacing, and color tokens across all modules.
- **Reusability**: Shared component templates (`abs-card`, `abs-btn`, `abs-input`, `abs-table`).
- **Accessibility**: High-contrast ratios, legible typography (Inter), and focus ring feedback.
- **Responsive Design**: Fluid grid layouts (`abs-grid-4`, `abs-layout`) adapting to mobile, tablet, and desktop screens.
- **Performance**: Lightweight modular CSS without heavy framework overhead.
- **Maintainability**: Centralized token variables in `variables.css`.

## Design Tokens
```css
--abs-primary: #0B5ED7;
--abs-primary-hover: #0A58CA;
--abs-success: #198754;
--abs-danger: #DC3545;
--abs-warning: #FFC107;
--abs-dark: #1E293B;
--abs-border: #E2E8F0;
--radius-lg: 16px;
--radius-md: 10px;
--radius-sm: 6px;
```

## Reusable Components
- **Cards**: `abs-card`, `abs-card-header`, `abs-card-body`
- **Buttons**: `abs-btn`, `abs-btn-primary`, `abs-btn-success`, `abs-btn-danger`, `abs-btn-outline`
- **Forms**: `abs-input`, `abs-select`, `abs-textarea`, `abs-label`
- **Tables**: `abs-table`
- **Navigation**: `abs-sidebar`, `abs-navbar`
- **Badges & Alerts**: `abs-badge`, `abs-alert`
- **Modals**: `abs-modal`, `abs-modal-overlay`
