from sales.services.aging_service import AgingService


class AgingSelector:

    @classmethod
    def get_aging_report(cls, organization):
        return AgingService.get_aging_summary(organization=organization)
