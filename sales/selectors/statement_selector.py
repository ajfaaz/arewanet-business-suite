from sales.services.statement_service import StatementService


class StatementSelector:

    @classmethod
    def get_statement_context(cls, customer, start_date=None, end_date=None):
        return StatementService.generate_statement(
            customer=customer,
            start_date=start_date,
            end_date=end_date
        )
