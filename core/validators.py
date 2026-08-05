from django.core.exceptions import ValidationError

def positive_amount(value):
    if value < 0:
        raise ValidationError("Amount cannot be negative.")

def non_empty_string(value):
    if not value or not str(value).strip():
        raise ValidationError("This field cannot be empty or whitespace only.")
