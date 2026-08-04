class ExportService:
    @staticmethod
    def export_to_csv(queryset, fields):
        """Service to handle exporting document querysets to CSV."""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(fields)

        for obj in queryset:
            row = [getattr(obj, field, "") for field in fields]
            writer.writerow(row)

        return output.getvalue()
