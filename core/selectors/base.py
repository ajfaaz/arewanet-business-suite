class BaseSelector:
    """
    Base enterprise selector class providing standardized query abstractions.
    """

    @staticmethod
    def list(queryset):
        return queryset

    @staticmethod
    def get(model, **kwargs):
        return model.objects.get(**kwargs)
