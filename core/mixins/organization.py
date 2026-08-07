from django.db import models


class OrganizationMixin(models.Model):
    organization = models.ForeignKey(
        "invoices.Organization",
        on_delete=models.CASCADE,
        related_name="%(class)s_set"
    )

    class Meta:
        abstract = True
