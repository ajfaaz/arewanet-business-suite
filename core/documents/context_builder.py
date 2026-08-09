class DocumentContextBuilder:

    @staticmethod
    def build(document, title=None, extra_context=None):
        org = getattr(document, "organization", None)

        status = getattr(document, "status", "").upper()
        badge_class = "badge-secondary"
        if status in ("APPROVED", "COMPLETED", "PAID", "RECEIVED"):
            badge_class = "badge-success"
        elif status in ("DRAFT", "PENDING", "PARTIAL_RECEIPT", "PARTIALLY_PAID", "SUBMITTED"):
            badge_class = "badge-warning"
        elif status in ("CANCELLED", "OVERDUE", "REJECTED", "EXPIRED"):
            badge_class = "badge-danger"

        doc_number = (
            getattr(document, "document_number", None)
            or getattr(document, "order_number", None)
            or getattr(document, "quotation_no", None)
            or getattr(document, "quotation_number", None)
            or getattr(document, "invoice_no", None)
            or getattr(document, "receipt_no", None)
            or str(getattr(document, "id", ""))
        )

        context = {
            "title": title or f"Document {doc_number}",
            "organization": org,
            "document": document,
            "document_number": doc_number,
            "status_badge_class": badge_class,
            "status_display": getattr(document, "get_status_display", lambda: status)(),
            "created_at": getattr(document, "created_at", None),
        }

        if extra_context:
            context.update(extra_context)

        return context
