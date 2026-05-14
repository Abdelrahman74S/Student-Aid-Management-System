"""Tests for the aid_management app.

Covers:
- Core model validation & behavior (SupportCycle, AidApplication, BudgetAllocation)
- Forms (StudentApplicationForm, CommitteeReviewForm)
- Key views (StudentApplicationCreateView, StudentApplicationSubmitView)
"""

import json
from decimal import Decimal
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User, UserRoles, StudentProfile, ReviewerProfile
from .models import (
    SupportCycle,
    AidApplication,
    ScoringRule,
    CommitteeReview,
    BudgetAllocation,
    SerialCounter,
)


class AidManagementModelTests(TestCase):
    """Model‑level unit tests."""

    def setUp(self):
        # --- Create an admin user to be the creator of cycles ---
        self.admin_user = User.objects.create_superuser(
            email="admin@science.tanta.edu.eg",
            password="adminpassword",
            full_name="Admin User",
            national_id="00000000000000"
        )

        # --- Create a student user (signals will auto‑create StudentProfile) ---
        self.student_user = User.objects.create_user(
            email="UG_1111111@science.tanta.edu.eg",
            password="pwd123",
            full_name="Student One",
            national_id="11111111111111",
        )
        
        # Reviewer user for later use
        self.reviewer_user = User.objects.create_user(
            email="UG_2222222@science.tanta.edu.eg",
            password="pwd123",
            full_name="Reviewer One",
            national_id="22222222222222",
            role=UserRoles.REVIEWER,
        )
        self.reviewer_user.is_staff = True
        self.reviewer_user.save()

        # --- A support cycle that is open for applications ---
        now = timezone.now()
        self.cycle = SupportCycle.objects.create(
            name="اختبار 2026",
            academic_year="2025-2026",
            semester=SupportCycle.SEMESTER_CHOICES[0][0],  # FIRST
            total_budget=100_000,
            application_start_date=now - timedelta(days=1),
            application_end_date=now + timedelta(days=30),
            status=SupportCycle.STATUS_CHOICES[1][0],  # OPEN
            created_by=self.admin_user,
        )

    def test_support_cycle_date_validation(self):
        """Invalid start/end dates must raise ValidationError."""
        cycle = SupportCycle(
            name="خطأ",
            academic_year="2026-2027",
            semester=SupportCycle.SEMESTER_CHOICES[0][0],
            total_budget=10_000,
            application_start_date=timezone.now(),
            application_end_date=timezone.now() - timedelta(days=1),  # end < start
            created_by=self.admin_user,
        )
        with self.assertRaises(ValidationError) as ctx:
            cycle.full_clean()
        self.assertIn("application_end_date", ctx.exception.message_dict)

    def test_aid_application_submit_success(self):
        """A draft application should transition to SUBMITTED correctly."""
        app = AidApplication.objects.create(
            student=self.student_user.student_profile,
            cycle=self.cycle,
        )
        # ensure draft state
        self.assertEqual(app.status, AidApplication.STATUS_CHOICES[0][0])  # DRAFT

        # call the model method that encapsulates the submit logic
        app.submit()

        self.assertEqual(app.status, "SUBMITTED")
        self.assertIsNotNone(app.submission_date)
        self.assertTrue(app.serial_number.startswith("طلب-"))

    def test_aid_application_invalid_transition(self):
        """Attempting an illegal status transition should raise."""
        app = AidApplication.objects.create(
            student=self.student_user.student_profile,
            cycle=self.cycle,
        )
        # cannot jump from DRAFT directly to APPROVED
        with self.assertRaises(ValidationError):
            app.transition_to("APPROVED")

        # legal transition
        app.transition_to("SUBMITTED")
        self.assertEqual(app.status, "SUBMITTED")

    def test_budget_allocation_budget_exceedance(self):
        """Allocation amount larger than cycle remaining budget must fail."""
        # Reserve part of the budget so that only 5,000 remains
        self.cycle.reserved_budget = 95_000
        self.cycle.save()

        # Create a normal application in APPROVED state (required for allocation)
        app = AidApplication.objects.create(
            student=self.student_user.student_profile,
            cycle=self.cycle,
            status="APPROVED",
        )

        # Allocation trying to allocate more than remaining (5,001 > 5,000)
        allocation = BudgetAllocation(
            cycle=self.cycle,
            application=app,
            amount_allocated=5_001,
        )
        with self.assertRaises(ValidationError) as ctx:
            allocation.full_clean()
        self.assertIn("amount_allocated", ctx.exception.message_dict)


class AidManagementFormTests(TestCase):
    """Form‑level tests for the student and reviewer forms."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin_form@science.tanta.edu.eg",
            password="adminpassword",
            full_name="Admin Form",
            national_id="00000000000001"
        )
        self.student_user = User.objects.create_user(
            email="UG_3333333@science.tanta.edu.eg",
            password="pwd123",
            full_name="Student Two",
            national_id="33333333333333",
        )
        self.reviewer_user = User.objects.create_user(
            email="UG_reviewer_form@science.tanta.edu.eg",
            password="pwd123",
            full_name="Reviewer Form",
            national_id="44444444444444",
            role=UserRoles.REVIEWER,
        )
        self.reviewer_user.is_staff = True
        self.reviewer_user.save()

        self.cycle = SupportCycle.objects.create(
            name="دورة 2026",
            academic_year="2025-2026",
            semester=SupportCycle.SEMESTER_CHOICES[0][0],
            total_budget=50_000,
            application_start_date=timezone.now() - timedelta(days=2),
            application_end_date=timezone.now() + timedelta(days=10),
            status=SupportCycle.STATUS_CHOICES[1][0],  # OPEN
            created_by=self.admin_user,
        )
        self.application = AidApplication.objects.create(
            student=self.student_user.student_profile,
            cycle=self.cycle,
        )

    def test_student_application_form_saves_financial_assessment(self):
        """The form must persist financial data as JSON."""
        from .forms import StudentApplicationForm

        form_data = {
            "student": self.student_user.student_profile.id,
            "cycle": self.cycle.id,
            "father_income": "1200.00",
            "mother_income": "800.00",
            "family_members": 4,
            "housing_status": "RENT",
        }
        form = StudentApplicationForm(data=form_data, instance=self.application)
        self.assertTrue(form.is_valid())
        saved_app = form.save()
        assessment = saved_app.financial_assessment
        self.assertEqual(assessment["father_income"], "1200.00")
        self.assertEqual(assessment["housing_status"], "RENT")

    def test_committee_review_form_dynamic_fields_and_save(self):
        """Form should generate a field per active scoring rule and store scores."""
        # create two scoring rules for the cycle
        ScoringRule.objects.create(
            cycle=self.cycle,
            criteria_type="INCOME_TIER",
            condition={"min": 0, "max": 3000},
            points=10,
            weight=1.0,
            is_active=True,
        )
        ScoringRule.objects.create(
            cycle=self.cycle,
            criteria_type="GPA",
            condition={"min": 0, "max": 4},
            points=20,
            weight=1.5,
            is_active=True,
        )
        from .forms import CommitteeReviewForm

        # instantiate the form for the created application
        form = CommitteeReviewForm(application=self.application, reviewer=self.reviewer_user)
        # expected dynamic fields
        self.assertIn("score_income_tier", form.fields)
        self.assertIn("score_gpa", form.fields)

        # submit valid scores
        form_data = {
            "conflict_of_interest": False,
            "qualitative_notes": "ملاحظة",
            "score_income_tier": 8,
            "score_gpa": 18,
        }
        bound_form = CommitteeReviewForm(data=form_data, application=self.application, reviewer=self.reviewer_user)
        self.assertTrue(bound_form.is_valid())
        review = bound_form.save()
        self.assertEqual(review.dimension_scores["income_tier"], 8)
        self.assertEqual(review.dimension_scores["gpa"], 18)
        # total should be calculated with weights (8*1 + 18*1.5 = 35)
        self.assertAlmostEqual(float(review.total_score), 35.0)


class AidManagementViewTests(TestCase):
    """Integration tests for a few key views."""

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            email="admin_view@science.tanta.edu.eg",
            password="adminpassword",
            full_name="Admin View",
            national_id="00000000000002"
        )
        self.student_user = User.objects.create_user(
            email="UG_4444444@science.tanta.edu.eg",
            password="pwd123",
            full_name="Student Three",
            national_id="44444444444444",
        )
        self.reviewer_user = User.objects.create_user(
            email="UG_5555555@science.tanta.edu.eg",
            password="pwd123",
            full_name="Reviewer Two",
            national_id="55555555555555",
            role=UserRoles.REVIEWER,
        )
        self.reviewer_user.is_staff = True
        self.reviewer_user.save()

        # Open cycle for GET/POST tests
        self.cycle = SupportCycle.objects.create(
            name="عرض التطبيقات",
            academic_year="2025-2026",
            semester=SupportCycle.SEMESTER_CHOICES[0][0],
            total_budget=100_000,
            application_start_date=timezone.now() - timedelta(days=1),
            application_end_date=timezone.now() + timedelta(days=30),
            status=SupportCycle.STATUS_CHOICES[1][0],  # OPEN
            created_by=self.admin_user,
        )

    def test_student_create_view_without_open_cycle_redirects(self):
        """If no open cycle exists the view must redirect with an error."""
        # close the existing cycle
        self.cycle.status = SupportCycle.STATUS_CHOICES[3][0]  # CLOSED
        self.cycle.save()

        self.client.login(email=self.student_user.email, password="pwd123")
        response = self.client.get(reverse("aid_management:application_create"))
        # Expect a redirect to the list view
        self.assertRedirects(
            response,
            reverse("aid_management:application_list"),
            fetch_redirect_response=False,
        )
        # The message framework stores the error; we can inspect it via the session
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("لا توجد دورة دعم" in str(m) for m in messages))

    def test_student_create_view_successful_post_creates_draft(self):
        """POSTing valid data should create a draft AidApplication."""
        self.client.login(email=self.student_user.email, password="pwd123")
        url = reverse("aid_management:application_create")
        form_data = {
            "student": self.student_user.student_profile.id,
            "cycle": self.cycle.id,
            "father_income": "1500",
            "mother_income": "900",
            "family_members": 5,
            "housing_status": "OWN",
            "documents-TOTAL_FORMS": "0",
            "documents-INITIAL_FORMS": "0",
            "documents-MIN_NUM_FORMS": "0",
            "documents-MAX_NUM_FORMS": "1000",
        }
        response = self.client.post(url, data=form_data, follow=True)

        # After successful save we are redirected to the list view
        self.assertRedirects(
            response,
            reverse("aid_management:application_list"),
            fetch_redirect_response=False,
        )
        # Verify that an AidApplication exists in DRAFT state
        app = AidApplication.objects.get(student=self.student_user.student_profile)
        self.assertEqual(app.status, "DRAFT")
        self.assertEqual(app.financial_assessment["father_income"], "1500")
        self.assertEqual(app.financial_assessment["housing_status"], "OWN")

    def test_student_submit_view_transitions_to_submitted(self):
        """Calling the submit view should change status and generate serial."""
        # create a draft application first
        app = AidApplication.objects.create(
            student=self.student_user.student_profile,
            cycle=self.cycle,
            status="DRAFT",
        )
        self.client.login(email=self.student_user.email, password="pwd123")
        url = reverse("aid_management:application_submit", args=[app.id])
        response = self.client.post(url, follow=True)

        # Should redirect back to detail view
        self.assertRedirects(
            response,
            reverse("aid_management:application_detail", args=[app.id]),
            fetch_redirect_response=False,
        )
        app.refresh_from_db()
        self.assertEqual(app.status, "SUBMITTED")
        self.assertIsNotNone(app.submission_date)
        self.assertTrue(app.serial_number.startswith("طلب-"))


class ScoringEngineTests(TestCase):
    """Tests for the Auto-Scoring Engine (services.py)."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin_engine@science.tanta.edu.eg",
            password="adminpassword",
            full_name="Admin Engine",
            national_id="00000000000099"
        )
        self.student_user = User.objects.create_user(
            email="UG_9999999@science.tanta.edu.eg",
            password="pwd123",
            full_name="Student Engine",
            national_id="99999999999999",
        )
        # تعديل بيانات الطالب
        profile = self.student_user.student_profile
        profile.gpa = 3.20
        profile.disability_status = True
        profile.save()

        now = timezone.now()
        self.cycle = SupportCycle.objects.create(
            name="دورة محرك التقييم",
            academic_year="2025-2026",
            semester="FIRST",
            total_budget=50_000,
            application_start_date=now - timedelta(days=1),
            application_end_date=now + timedelta(days=30),
            status="OPEN",
            created_by=self.admin_user,
        )

        # قواعد التقييم
        ScoringRule.objects.create(
            cycle=self.cycle,
            criteria_type="INCOME_TIER",
            condition={"min": 0, "max": 5000},
            points=20,
            weight=Decimal("1.50"),
            is_active=True,
        )
        ScoringRule.objects.create(
            cycle=self.cycle,
            criteria_type="FAMILY_SIZE",
            condition={"min": 1, "max": 10},
            points=10,
            weight=Decimal("1.00"),
            is_active=True,
        )
        ScoringRule.objects.create(
            cycle=self.cycle,
            criteria_type="GPA",
            condition={"min": 0, "max": 4},
            points=15,
            weight=Decimal("1.20"),
            is_active=True,
        )
        ScoringRule.objects.create(
            cycle=self.cycle,
            criteria_type="SPECIAL_CASES",
            condition={},
            points=10,
            weight=Decimal("1.00"),
            is_active=True,
        )
        ScoringRule.objects.create(
            cycle=self.cycle,
            criteria_type="SOCIAL_RESEARCH",
            condition={},
            points=15,
            weight=Decimal("1.00"),
            is_active=True,
        )

        self.application = AidApplication.objects.create(
            student=self.student_user.student_profile,
            cycle=self.cycle,
            financial_assessment={
                "father_income": "1500",
                "mother_income": "500",
                "family_members": 7,
                "housing_status": "RENT",
            },
        )

    def test_scoring_engine_calculates_all_dimensions(self):
        """Engine should evaluate all active rules."""
        from .services import ScoringEngine

        engine = ScoringEngine(self.application)
        result = engine.evaluate()

        # 5 rules = 5 dimensions
        self.assertEqual(len(result.dimensions), 5)

    def test_income_tier_inverse_scoring(self):
        """Lower income should get higher points (inverse)."""
        from .services import ScoringEngine

        engine = ScoringEngine(self.application)
        result = engine.evaluate()

        income_dim = next(d for d in result.dimensions if d.criteria_type == 'INCOME_TIER')
        # Total income = 1500 + 500 = 2000, range = 0-5000
        # Inverse ratio = 1 - (2000/5000) = 0.6, points = 20 * 0.6 = 12
        self.assertEqual(income_dim.awarded_points, 12)
        self.assertTrue(income_dim.matched)
        self.assertTrue(income_dim.is_auto)

    def test_family_size_direct_scoring(self):
        """Larger family should get more points (direct)."""
        from .services import ScoringEngine

        engine = ScoringEngine(self.application)
        result = engine.evaluate()

        family_dim = next(d for d in result.dimensions if d.criteria_type == 'FAMILY_SIZE')
        # family_members = 7, range = 1-10
        # ratio = (7-1)/(10-1) = 6/9 ≈ 0.667, points = 10 * 0.667 ≈ 7
        self.assertEqual(family_dim.awarded_points, 7)
        self.assertTrue(family_dim.matched)

    def test_gpa_direct_scoring(self):
        """Higher GPA should get more points."""
        from .services import ScoringEngine

        engine = ScoringEngine(self.application)
        result = engine.evaluate()

        gpa_dim = next(d for d in result.dimensions if d.criteria_type == 'GPA')
        # gpa = 3.20, range = 0-4
        # ratio = 3.20/4 = 0.8, points = 15 * 0.8 = 12
        self.assertEqual(gpa_dim.awarded_points, 12)
        self.assertTrue(gpa_dim.matched)

    def test_special_cases_with_disability(self):
        """Student with disability should get full points."""
        from .services import ScoringEngine

        engine = ScoringEngine(self.application)
        result = engine.evaluate()

        special_dim = next(d for d in result.dimensions if d.criteria_type == 'SPECIAL_CASES')
        self.assertEqual(special_dim.awarded_points, 10)
        self.assertTrue(special_dim.matched)

    def test_social_research_is_manual(self):
        """Social research should be marked as manual."""
        from .services import ScoringEngine

        engine = ScoringEngine(self.application)
        result = engine.evaluate()

        social_dim = next(d for d in result.dimensions if d.criteria_type == 'SOCIAL_RESEARCH')
        self.assertEqual(social_dim.awarded_points, 0)
        self.assertFalse(social_dim.is_auto)
        self.assertTrue(result.has_manual_dimensions)

    def test_total_auto_score_calculation(self):
        """Total auto score should be sum of weighted auto-scored dimensions."""
        from .services import ScoringEngine

        engine = ScoringEngine(self.application)
        result = engine.evaluate()

        # income: 12 * 1.5 = 18
        # family: 7 * 1.0 = 7
        # gpa: 12 * 1.2 = 14.4
        # special: 10 * 1.0 = 10
        # social: 0 (manual)
        expected_total = 18 + 7 + 14.4 + 10
        self.assertAlmostEqual(result.total_auto_score, expected_total, places=1)

    def test_calculate_auto_score_model_method(self):
        """The model method should persist the score."""
        self.application.calculate_auto_score()
        self.application.refresh_from_db()

        self.assertGreater(float(self.application.auto_score), 0)
        self.assertIn('dimensions', self.application.auto_score_breakdown)
        self.assertEqual(
            len(self.application.auto_score_breakdown['dimensions']), 5
        )

    def test_suggested_scores_dict(self):
        """get_suggested_scores should return a dict keyed by criteria_type."""
        from .services import ScoringEngine

        engine = ScoringEngine(self.application)
        suggestions = engine.get_suggested_scores()

        self.assertIn('income_tier', suggestions)
        self.assertIn('gpa', suggestions)
        self.assertIn('special_cases', suggestions)
        self.assertEqual(suggestions['income_tier']['suggested_points'], 12)
        self.assertFalse(suggestions['social_research']['is_auto'])

