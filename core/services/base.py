class BaseService:
    """
    Base enterprise service class providing standard CRUD operations.
    """

    @staticmethod
    def create(model, **kwargs):
        return model.objects.create(**kwargs)

    @staticmethod
    def update(instance, **kwargs):
        for key, value in kwargs.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    @staticmethod
    def delete(instance):
        instance.delete()
