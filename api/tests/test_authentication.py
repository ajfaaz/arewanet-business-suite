from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from invoices.models import Organization, UserProfile

User = get_user_model()


class AuthenticationAPITestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="authuser",
            password="oldpassword123",
            email="auth@example.com",
            first_name="Auth",
            last_name="User"
        )
        self.org = Organization.objects.create(name="Auth Test Org", slug="auth-test-org")
        self.profile = UserProfile.objects.create(user=self.user, organization=self.org, role="ADMIN")
        self.client = APIClient()

    def test_login_success(self):
        response = self.client.post("/api/v1/auth/login/", {
            "username": "authuser",
            "password": "oldpassword123"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data["data"])
        self.assertIn("refresh", response.data["data"])
        self.assertEqual(response.data["data"]["user"]["username"], "authuser")

    def test_login_failure_invalid_password(self):
        response = self.client.post("/api/v1/auth/login/", {
            "username": "authuser",
            "password": "wrongpassword"
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data["success"])

    def test_login_failure_missing_username(self):
        response = self.client.post("/api/v1/auth/login/", {
            "password": "oldpassword123"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_me_endpoint(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["username"], "authuser")
        self.assertEqual(response.data["data"]["role"], "ADMIN")
        self.assertEqual(response.data["data"]["organization"]["name"], "Auth Test Org")

    def test_jwt_token_refresh(self):
        login_res = self.client.post("/api/v1/auth/login/", {
            "username": "authuser",
            "password": "oldpassword123"
        })
        refresh_token = login_res.data["data"]["refresh"]

        refresh_res = self.client.post("/api/v1/auth/refresh/", {
            "refresh": refresh_token
        })
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_res.data)

    def test_logout(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/v1/auth/logout/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

    def test_change_password_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/v1/auth/change-password/", {
            "old_password": "oldpassword123",
            "new_password": "newpassword456"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        # Verify login with new password
        self.client.logout()
        login_res = self.client.post("/api/v1/auth/login/", {
            "username": "authuser",
            "password": "newpassword456"
        })
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)

    def test_change_password_wrong_old_password(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/v1/auth/change-password/", {
            "old_password": "incorrectpassword",
            "new_password": "newpassword456"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
