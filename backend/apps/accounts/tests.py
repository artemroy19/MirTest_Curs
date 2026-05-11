from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class AccountsApiTests(APITestCase):
    password = "StrongPass123!"

    def create_user(self, email="user@example.com", role=User.Roles.STUDENT, **extra):
        return User.objects.create_user(
            email=email,
            username=email.split("@", 1)[0],
            password=self.password,
            role=role,
            **extra,
        )

    def test_user_can_register(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "student@example.com",
                "username": "student",
                "name": "Student",
                "role": User.Roles.STUDENT,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(User.objects.filter(email="student@example.com").exists())

    def test_user_cannot_register_as_admin(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "admin@example.com",
                "username": "admin",
                "name": "Admin",
                "role": User.Roles.ADMIN,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="admin@example.com").exists())

    def test_user_can_login_and_receive_tokens(self):
        self.create_user(email="login@example.com")

        response = self.client.post(
            "/api/auth/login/",
            {"email": "login@example.com", "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "login@example.com")

    def test_authenticated_user_can_get_me(self):
        user = self.create_user(email="me@example.com")
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], user.email)

    def test_unauthenticated_user_cannot_get_me(self):
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_change_password(self):
        user = self.create_user(email="password@example.com")
        self.client.force_authenticate(user=user)

        response = self.client.post(
            "/api/auth/change-password/",
            {"old_password": self.password, "new_password": "NewStrongPass123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewStrongPass123!"))

    def test_user_can_update_profile(self):
        user = self.create_user(email="profile@example.com")
        self.client.force_authenticate(user=user)

        response = self.client.patch(
            "/api/auth/profile/",
            {"first_name": "Artem", "last_name": "Roytman"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Artem")
        self.assertEqual(user.last_name, "Roytman")
