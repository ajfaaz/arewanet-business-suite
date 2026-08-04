from datetime import datetime
from django.db.models import Max


def generate_document_number(model, field_name, prefix):
    """
    Generate document numbers like:

    ANV-2026-0001
    RCT-2026-0001
    QTN-2026-0001
    """

    year = datetime.now().year

    last = model.objects.aggregate(
        max_id=Max("id")
    )["max_id"] or 0

    next_number = last + 1

    return f"{prefix}-{year}-{next_number:04d}"
