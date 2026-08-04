from datetime import datetime

class DocumentNumberService:

    PREFIXES = {
        "invoice": "INV",
        "quotation": "QTN",
        "receipt": "RCT",
        "purchase": "PO",
    }

    @classmethod
    def generate(cls, document_type, last_number):

        year = datetime.now().year

        prefix = cls.PREFIXES.get(document_type, "DOC")

        return f"{prefix}-{year}-{last_number:04d}"
