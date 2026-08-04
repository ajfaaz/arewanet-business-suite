class TotalsMixin:

    def update_totals(self):
        subtotal = sum(
            item.total
            for item in self.items.all()
        )
        self.subtotal = subtotal
        vat_val = getattr(self, 'vat', 0) or 0
        self.total_due = subtotal + vat_val
        self.save()
