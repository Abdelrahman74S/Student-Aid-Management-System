from django.apps import AppConfig


class AidManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'aid_management'

    def ready(self):
        import aid_management.signals