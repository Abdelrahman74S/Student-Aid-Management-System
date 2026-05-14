from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from accounts.models import UserRoles, Program
from aid_management.models import SupportCycle, AidApplication, CommitteeReview
from assets_reporting.models import SystemTemplate, SocialResearchForm

User = get_user_model()

class RBACTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create Program
        self.program_cs = Program.objects.create(name="Computer Science", code="CS")
        self.program_bio = Program.objects.create(name="Biology", code="BIO")

        # Create Users
        self.student = User.objects.create_user(
            email="UG_111@science.tanta.edu.eg",
            password="password",
            full_name="Student User",
            national_id="11111111111111",
            role=UserRoles.STUDENT
        )
        self.student.student_profile.program = self.program_cs
        self.student.student_profile.save()

        self.reviewer_cs = User.objects.create_user(
            email="UG_222@science.tanta.edu.eg",
            password="password",
            full_name="Reviewer CS",
            national_id="22222222222222",
            role=UserRoles.REVIEWER
        )
        self.reviewer_cs.reviewer_profile.assigned_programs.add(self.program_cs)

        self.committee_head = User.objects.create_user(
            email="UG_333@science.tanta.edu.eg",
            password="password",
            full_name="Committee Head",
            national_id="33333333333333",
            role=UserRoles.COMMITTEE_HEAD
        )

        self.auditor = User.objects.create_user(
            email="UG_444@science.tanta.edu.eg",
            password="password",
            full_name="Auditor User",
            national_id="44444444444444",
            role=UserRoles.AUDITOR
        )

        # Create data for testing
        self.cycle = SupportCycle.objects.create(
            name="Test Cycle",
            academic_year="2024",
            semester="FIRST",
            total_budget=1000,
            application_start_date="2024-01-01T00:00:00Z",
            application_end_date="2024-12-31T23:59:59Z",
            status="OPEN",
            created_by=self.committee_head
        )
        self.application = AidApplication.objects.create(
            student=self.student.student_profile,
            cycle=self.cycle,
            status="SUBMITTED",
            serial_number="APP-CS-001"
        )
        self.review = CommitteeReview.objects.create(
            application=self.application,
            reviewer=self.reviewer_cs,
            status="DRAFT",
            dimension_scores={}
        )
        self.template_student = SystemTemplate.objects.create(
            name="Student Template",
            role_required=UserRoles.STUDENT
        )
        self.template_reviewer = SystemTemplate.objects.create(
            name="Reviewer Template",
            role_required=UserRoles.REVIEWER
        )

    def test_student_cannot_access_committee_views(self):
        self.client.login(email=self.student.email, password="password")
        response = self.client.get(reverse('assets_reporting:meeting_list'))
        # Should redirect to dashboard (immediate redirect)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:dashboard'), response.url)

    def test_reviewer_cannot_access_audit_views(self):
        self.client.login(email=self.reviewer_cs.email, password="password")
        response = self.client.get(reverse('audit:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:dashboard'), response.url)

    def test_auditor_cannot_access_scoring_views(self):
        self.client.login(email=self.auditor.email, password="password")
        response = self.client.get(reverse('aid_management:application_scoring', kwargs={'pk': self.review.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:dashboard'), response.url)

    def test_reviewer_program_isolation(self):
        """Reviewer should NOT be able to create social research for a student in a different program."""
        student_bio_user = User.objects.create_user(
            email="UG_555@science.tanta.edu.eg",
            password="password",
            full_name="Bio Student",
            national_id="55555555555555",
            role=UserRoles.STUDENT
        )
        student_bio_user.student_profile.program = self.program_bio
        student_bio_user.student_profile.save()
        
        app_bio = AidApplication.objects.create(
            student=student_bio_user.student_profile,
            cycle=self.cycle,
            status="SUBMITTED",
            serial_number="APP-BIO-001"
        )

        self.client.login(email=self.reviewer_cs.email, password="password")
        response = self.client.get(reverse('assets_reporting:social_research_create', kwargs={'app_id': app_bio.id}))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:dashboard'), response.url)

    def test_secure_template_download_enforcement(self):
        """Student should NOT be able to download a reviewer-only template."""
        self.client.login(email=self.student.email, password="password")
        response = self.client.get(reverse('assets_reporting:template_download', kwargs={'pk': self.template_reviewer.pk}))
        self.assertRedirects(response, reverse('assets_reporting:template_list'))
        
        response_ok = self.client.get(reverse('assets_reporting:template_download', kwargs={'pk': self.template_student.pk}))
        self.assertNotEqual(response_ok.status_code, 302)

    def test_reviewer_idor_protection(self):
        """Reviewer should NOT be able to access another reviewer's scoring page."""
        reviewer_other = User.objects.create_user(
            email="UG_other@science.tanta.edu.eg",
            password="password",
            full_name="Other Reviewer",
            national_id="00000000000000",
            role=UserRoles.REVIEWER
        )
        reviewer_other.reviewer_profile.assigned_programs.add(self.program_cs)
        
        self.client.login(email=reviewer_other.email, password="password")
        response = self.client.get(reverse('aid_management:application_scoring', kwargs={'pk': self.review.pk}))
        self.assertEqual(response.status_code, 404)
