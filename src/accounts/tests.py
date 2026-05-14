"""Tests for the accounts app.

This suite verifies core model behavior such as user creation, role handling,
and the role‑validated profile mixin.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import User, UserRoles, StudentProfile, ReviewerProfile


class UserModelTests(TestCase):
    def test_create_user_with_email_and_default_role(self):
        """A regular user should be created with the STUDENT role by default."""
        email = "UG_1234567@science.tanta.edu.eg"
        user = User.objects.create_user(email=email, password="testpass123", full_name="Test User", national_id="12345678901234")
        self.assertIsNotNone(user.id)
        self.assertEqual(user.email, email.lower())
        self.assertTrue(user.check_password("testpass123"))
        self.assertEqual(user.role, UserRoles.STUDENT)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        """Superuser creation should enforce staff and superuser flags and ADMIN role."""
        email = "UG_9999999@science.tanta.edu.eg"
        admin = User.objects.create_superuser(email=email, password="adminpass", full_name="Admin User", national_id="99999999999999")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, UserRoles.ADMIN)

    def test_unique_email_enforced(self):
        email = "UG_1111111@science.tanta.edu.eg"
        User.objects.create_user(email=email, password="pwd", full_name="First", national_id="11111111111111")
        with self.assertRaises(ValidationError):
            user = User(email=email, full_name="Second", national_id="22222222222222")
            user.full_clean()


class ProfileMixinTests(TestCase):
    def setUp(self):
        # Creating a user will trigger the create_user_profile signal
        self.user = User.objects.create_user(
            email="UG_2222222@science.tanta.edu.eg",
            password="pwd",
            full_name="Student One",
            national_id="22222222222222",
        )
        self.reviewer = User.objects.create_user(
            email="UG_3333333@science.tanta.edu.eg",
            password="pwd",
            full_name="Reviewer One",
            national_id="33333333333333",
            role=UserRoles.REVIEWER,
        )
        # Note: Signals create profiles automatically

    def test_student_profile_auto_creation(self):
        """Creating a student user should automatically create a StudentProfile."""
        self.assertTrue(hasattr(self.user, 'student_profile'))
        self.assertEqual(self.user.student_profile.student_id, self.user.national_id)

    def test_reviewer_profile_auto_creation(self):
        """Creating a reviewer user should automatically create a ReviewerProfile."""
        self.assertTrue(hasattr(self.reviewer, 'reviewer_profile'))

    def test_student_profile_role_validation(self):
        """Verify that StudentProfile validation works correctly."""
        profile = self.user.student_profile
        profile.full_clean()  # Should be valid
        
        # Test validation by manually setting a wrong role (mimicking invalid state before clean)
        self.user.role = UserRoles.REVIEWER
        self.user.save()
        
        # The signal update_user_profile_on_role_change might have deleted/recreated profile
        # Let's check the mixin logic directly on an unsaved object to be safe
        bad_profile = StudentProfile(user=self.reviewer, student_id="BAD123")
        with self.assertRaises(ValidationError):
            bad_profile.full_clean()


