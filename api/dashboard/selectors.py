from api.dashboard.services import DashboardAPIService


class DashboardSelector:

    @staticmethod
    def get_summary(organization):
        return DashboardAPIService.get_summary(organization)

    @staticmethod
    def get_revenue_trend(organization):
        return DashboardAPIService.get_revenue_trend(organization)

    @staticmethod
    def get_receivables(organization):
        return DashboardAPIService.get_receivables(organization)

    @staticmethod
    def get_top_customers(organization):
        return DashboardAPIService.get_top_customers(organization)

    @staticmethod
    def get_top_products(organization):
        return DashboardAPIService.get_top_products(organization)

    @staticmethod
    def get_recent_activity(organization):
        return DashboardAPIService.get_recent_activity(organization)

    @staticmethod
    def get_notifications(organization):
        return DashboardAPIService.get_notifications(organization)
