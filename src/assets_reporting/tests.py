from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import UserRoles, StudentProfile, ReviewerProfile
from aid_management.models import AidApplication, SupportCycle, BudgetAllocation
from assets_reporting.models import (
    DocumentType, ApplicationDocument, OfficialReport, 
    SocialResearchForm, CommitteeMeetingMinute, DisbursementVoucher, SystemTemplate
)
from assets_reporting.forms import (
    ApplicationDocumentForm, DigitalSocialResearchForm, 
    CommitteeMeetingForm, DisbursementVoucherForm
)

User = get_user_model()

class AssetsReportingModelTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin_assets@science.tanta.edu.eg",
            password="adminpassword",
            full_name="Admin Assets",
            national_id="00000000000010"
        )
        self.student_user = User.objects.create_user(
            email="UG_1234567@science.tanta.edu.eg",
            password="pwd123",
            full_name="Student Test",
            national_id="12345678901234",
            role=UserRoles.STUDENT
        )
        self.cycle = SupportCycle.objects.create(
            name="دورة الاختبار",
            academic_year="2025-2026",
            semester=SupportCycle.SEMESTER_CHOICES[0][0],
            total_budget=50000,
            application_start_date=timezone.now() - timedelta(days=1),
            application_end_date=timezone.now() + timedelta(days=30),
            status='OPEN',
            created_by=self.admin_user,
        )
        self.application = AidApplication.objects.create(
            student=self.student_user.student_profile,
            cycle=self.cycle,
            status="DRAFT",
        )
        self.doc_type = DocumentType.objects.create(code="ID", name="بطاقة الرقم القومي")

    def test_document_type_creation(self):
        self.assertEqual(str(self.doc_type), "بطاقة الرقم القومي")

    def test_application_document_creation(self):
        doc = ApplicationDocument.objects.create(
            application=self.application,
            document_type=self.doc_type,
            file=SimpleUploadedFile("test.pdf", b"file_content")
        )
        self.assertIn("بطاقة الرقم القومي", str(doc))

    def test_disbursement_voucher_hash(self):
        self.application.status = 'APPROVED'
        self.application.save()
        allocation = BudgetAllocation.objects.create(
            cycle=self.cycle,
            application=self.application,
            amount_allocated=1000,
            status='PENDING'
        )
        voucher = DisbursementVoucher.objects.create(
            voucher_number="VCH-001",
            application=self.application,
            allocation=allocation,
            amount=1000,
            expiry_date=timezone.now().date() + timedelta(days=30)
        )
        self.assertIsNotNone(voucher.verification_hash)
        self.assertTrue(voucher.verify(voucher.verification_hash))


class AssetsReportingFormTests(TestCase):
    def setUp(self):
        self.doc_type = DocumentType.objects.create(code="ID", name="بطاقة الرقم القومي")

    def test_application_document_form_valid(self):
        file_data = {'file': SimpleUploadedFile('test.jpg', b'file_content', content_type='image/jpeg')}
        form_data = {'document_type': self.doc_type.id}
        form = ApplicationDocumentForm(data=form_data, files=file_data)
        self.assertTrue(form.is_valid())

    def test_digital_social_research_form_valid(self):
        form_data = {
            'housing_type': 'RENT',
            'monthly_rent': 500,
            'researcher_name': 'أحمد محمود',
            'researcher_opinion': 'مستحق للدعم',
        }
        form = DigitalSocialResearchForm(data=form_data)
        self.assertTrue(form.is_valid())


class AssetsReportingViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student_user = User.objects.create_user(
            email="UG_test@science.tanta.edu.eg",
            password="pwd123",
            full_name="Student Test",
            national_id="99999999999999",
            role=UserRoles.STUDENT
        )
        self.reviewer_user = User.objects.create_user(
            email="UG_rev@science.tanta.edu.eg",
            password="pwd123",
            full_name="Reviewer Test",
            national_id="88888888888888",
            role=UserRoles.REVIEWER
        )
        self.admin_user = User.objects.create_superuser(
            email="admin_assets2@science.tanta.edu.eg",
            password="adminpassword",
            full_name="Admin Assets 2",
            national_id="77777777777777"
        )
        self.cycle = SupportCycle.objects.create(
            name="دورة الاختبار 2",
            academic_year="2025-2026",
            semester=SupportCycle.SEMESTER_CHOICES[0][0],
            total_budget=50000,
            application_start_date=timezone.now() - timedelta(days=1),
            application_end_date=timezone.now() + timedelta(days=30),
            status='OPEN',
            created_by=self.admin_user,
        )
        self.application = AidApplication.objects.create(
            student=self.student_user.student_profile,
            cycle=self.cycle,
            status="DRAFT",
        )
        self.doc_type = DocumentType.objects.create(code="ID", name="بطاقة")

    def test_student_document_list_view(self):
        self.client.login(email=self.student_user.email, password="pwd123")
        response = self.client.get(reverse('assets_reporting:document_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'assets_reporting/student/document_list.html')

    def test_social_research_create_view_auth(self):
        # Should redirect if not reviewer
        self.client.login(email=self.student_user.email, password="pwd123")
        response = self.client.get(reverse('assets_reporting:social_research_create', args=[self.application.id]))
        self.assertEqual(response.status_code, 302) # Redirects to dashboard
