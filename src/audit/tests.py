from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from accounts.models import UserRoles
from aid_management.models import SupportCycle, AidApplication
from .models import (
    DataAuditLog, ProcessActionLog, AccessLog, BudgetAuditLog, 
    SystemOverrideLog, FinancialIntegrityLog, ApplicationHistory
)

User = get_user_model()

class AuditModelTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin_audit@science.tanta.edu.eg",
            password="adminpassword",
            full_name="Admin Audit",
            national_id="00000000000020"
        )
        self.cycle = SupportCycle.objects.create(
            name="دورة المراجعة",
            academic_year="2025-2026",
            semester="FIRST",
            total_budget=50000,
            application_start_date=timezone.now() - timedelta(days=1),
            application_end_date=timezone.now() + timedelta(days=30),
            status='OPEN',
            created_by=self.admin_user,
        )

    def test_data_audit_log_creation(self):
        log = DataAuditLog.objects.create(
            user=self.admin_user,
            entity_type="SupportCycle",
            entity_id=str(self.cycle.id),
            action="CREATE",
            new_values={"name": "دورة المراجعة"}
        )
        self.assertEqual(log.action, "CREATE")
        self.assertEqual(log.entity_type, "SupportCycle")

    def test_process_action_log_creation(self):
        log = ProcessActionLog.objects.create(
            user=self.admin_user,
            action_name="فتح دورة الدعم",
            cycle_name=self.cycle.name,
            notes="تم فتح الدورة للاختبار"
        )
        self.assertEqual(log.action_name, "فتح دورة الدعم")

    def test_access_log_creation(self):
        log = AccessLog.objects.create(
            user=self.admin_user,
            event_type="LOGIN",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0"
        )
        self.assertEqual(log.event_type, "LOGIN")

    def test_budget_audit_log_creation(self):
        log = BudgetAuditLog.objects.create(
            cycle=self.cycle,
            user=self.admin_user,
            amount_before=40000,
            amount_after=50000,
            reason="زيادة الميزانية"
        )
        self.assertEqual(log.amount_after, 50000)


class AuditViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            email="admin_audit_view@science.tanta.edu.eg",
            password="adminpassword",
            full_name="Admin Audit View",
            national_id="00000000000021"
        )
        self.auditor_user = User.objects.create_user(
            email="auditor@science.tanta.edu.eg",
            password="pwd123",
            full_name="Auditor Test",
            national_id="11111111111111",
            role=UserRoles.AUDITOR
        )
        self.student_user = User.objects.create_user(
            email="student_audit@science.tanta.edu.eg",
            password="pwd123",
            full_name="Student Test",
            national_id="22222222222222",
            role=UserRoles.STUDENT
        )
    
    def test_dashboard_access_for_auditor(self):
        self.client.login(email=self.auditor_user.email, password="pwd123")
        response = self.client.get(reverse('audit:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "audit/dashboard.html")

    def test_dashboard_denied_for_student(self):
        self.client.login(email=self.student_user.email, password="pwd123")
        response = self.client.get(reverse('audit:dashboard'), follow=True)
        # Should redirect to accounts dashboard, which redirects to student app list
        self.assertRedirects(response, reverse('aid_management:application_list'))
        messages_list = list(response.context['messages'])
        self.assertTrue(any("سجلات حساسة" in str(m) for m in messages_list))

    def test_data_audit_list_view(self):
        self.client.login(email=self.admin_user.email, password="adminpassword")
        response = self.client.get(reverse('audit:data_audit_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('data_logs', response.context)

    def test_access_log_list_view(self):
        self.client.login(email=self.admin_user.email, password="adminpassword")
        response = self.client.get(reverse('audit:access_log_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_logs', response.context)

    def test_override_log_list_view(self):
        self.client.login(email=self.admin_user.email, password="adminpassword")
        response = self.client.get(reverse('audit:override_log_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('overrides', response.context)

    def test_timeline_view(self):
        self.client.login(email=self.admin_user.email, password="adminpassword")
        response = self.client.get(reverse('audit:timeline'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('history_events', response.context)
