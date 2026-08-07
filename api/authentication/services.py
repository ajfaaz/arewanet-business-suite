from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken


class AuthenticationService:

    @staticmethod
    def login(username, password):
        user = authenticate(username=username, password=password)
        if not user or not user.is_active:
            return None

        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": user,
        }

    @staticmethod
    def change_password(user, old_password, new_password):
        if not user.check_password(old_password):
            return False, "Old password is incorrect."

        user.set_password(new_password)
        user.save()
        return True, "Password changed successfully."
