# ABS Component Guide

Internal developer guide for the ArewaNet Business Suite (ABS) reusable UI component library.

---

## 1. ABS Button Component
**Path**: `components/buttons/button.html`

### Parameters
- `text`: Button label
- `url`: Link destination (default `#`)
- `type`: Button color scheme (`primary`, `success`, `danger`, `warning`, `outline`)
- `icon`: Bootstrap icon name (e.g. `plus-circle`, `wallet`, `trash`)
- `size`: Optional size (`sm`, `lg`)

### Usage Example
```django
{% include "components/buttons/button.html" with text="New Invoice" url=new_invoice_url type="success" icon="plus-circle" %}
```

---

## 2. ABS Stat Card Component
**Path**: `components/cards/stat_card.html`

### Parameters
- `title`: Metric title
- `value`: Display numeric or currency value
- `icon`: Metric icon name

### Usage Example
```django
{% include "components/cards/stat_card.html" with title="Total Revenue" value="₦14,250,000" icon="wallet" %}
```

---

## 3. ABS Page Header Component
**Path**: `components/layout/page_header.html`

### Parameters
- `title`: Page heading
- `subtitle`: Subtitle text
- `button_text`: Action button text
- `button_url`: Action button link
- `button_icon`: Action button icon

### Usage Example
```django
{% include "components/layout/page_header.html" with title="Customers" subtitle="Manage client directory" button_text="Add Customer" button_url=create_url button_icon="plus-circle" %}
```

---

## 4. ABS Table Component
**Path**: `components/tables/table.html`

### Parameters
- `columns`: Array of column header strings

---

## 5. ABS Empty State Component
**Path**: `components/empty/empty_state.html`

### Parameters
- `title`: Empty header title
- `message`: Description text
- `icon`: Icon class
- `button_text`: Call to action button text
- `button_url`: Call to action link

### Usage Example
```django
{% include "components/empty/empty_state.html" with title="No Invoices Yet" message="Create your first invoice to get started." button_text="Create Invoice" button_url=create_url %}
```

---

## 6. Toast Notification Component
**Path**: `components/notifications/toast.html`

Renders system notifications dynamically with auto-dismiss formatting.

---

## 7. Loading Spinner Component
**Path**: `components/loading/spinner.html`

### Parameters
- `text`: Loading text (default `"Saving..."`)

---

## 8. Modal Component
**Path**: `components/modals/modal.html`

### Parameters
- `id`: Modal HTML ID
- `title`: Modal title
- `body_text`: Confirmation message text
- `confirm_url`: Endpoint link for action
- `confirm_text`: Confirm button text
- `confirm_type`: Button type (`danger`, `primary`)

---

## 9. Breadcrumb Component
**Path**: `components/layout/breadcrumb.html`

### Parameters
- `parent_title`: Parent page name
- `parent_url`: Parent page URL
- `current_title`: Current page title
