from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

# استيراد الـ Mixins الخاصة بالصلاحيات من تطبيق الحسابات
from accounts.mixins import (
    StudentRequiredMixin, ReviewerRequiredMixin, 
    CommitteeHeadRequiredMixin
)

from .models import (
    ApplicationDocument, SocialResearchForm, 
    CommitteeMeetingMinute, DisbursementVoucher, OfficialReport
)
from .forms import (
    ApplicationDocumentForm, DigitalSocialResearchForm, 
    CommitteeMeetingForm, DisbursementVoucherForm
)
from aid_management.models import AidApplication

# --- 1. قسم الطالب (المستندات) ---

class StudentDocumentListView(LoginRequiredMixin, StudentRequiredMixin, ListView):
    model = ApplicationDocument
    template_name = 'assets_reporting/student/document_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        return ApplicationDocument.objects.filter(application__student__user=self.request.user)
    
class DocumentUploadView(LoginRequiredMixin, StudentRequiredMixin, CreateView):
    """واجهة تتيح للطالب رفع المستندات الثبوتية"""
    model = ApplicationDocument
    form_class = ApplicationDocumentForm
    template_name = 'assets_reporting/student/document_form.html'
    success_url = reverse_lazy('assets_reporting:document_list')

    def form_valid(self, form):
        # ربط المستند بآخر طلب نشط قدمه الطالب تلقائياً
        try:
            application = AidApplication.objects.filter(
                student__user=self.request.user
            ).latest('created_at')
            form.instance.application = application
            return super().form_valid(form)
        except AidApplication.DoesNotExist:
            form.add_error(None, "لم يتم العثور على طلب تقديم نشط لإرفاق المستندات به.")
            return self.form_invalid(form)


class DocumentDeleteView(LoginRequiredMixin, StudentRequiredMixin, DeleteView):
    """إتاحة حذف مستند مرفق قبل بدء عملية المراجعة"""
    model = ApplicationDocument
    success_url = reverse_lazy('assets_reporting:document_list')
    template_name = 'assets_reporting/student/document_confirm_delete.html'


class DisbursementVoucherDetailView(LoginRequiredMixin, StudentRequiredMixin, DetailView):
    """عرض قسيمة الصرف للطالب بعد صدور القرار النهائي"""
    model = DisbursementVoucher
    template_name = 'assets_reporting/student/voucher_detail.html'
    context_object_name = 'voucher'

    def get_object(self):
        # التأكد من أن الطالب يرى القسيمة الخاصة بطلبه فقط
        return get_object_or_404(
            DisbursementVoucher, 
            application_id=self.kwargs.get('app_id'),
            application__student__user=self.request.user
        )
        
# --- 2. قسم الباحث الاجتماعي (البحث الميداني) ---

class SocialResearchCreateView(LoginRequiredMixin, ReviewerRequiredMixin, CreateView):
    """واجهة للباحث لملء استمارة البحث الاجتماعي الرقمية"""
    model = SocialResearchForm
    form_class = DigitalSocialResearchForm
    template_name = 'assets_reporting/reviewer/social_research_form.html'

    def form_valid(self, form):
        form.instance.application_id = self.kwargs.get('app_id')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('aid_management:reviewer_task_list')


class SocialResearchUpdateView(LoginRequiredMixin, ReviewerRequiredMixin, UpdateView):
    """إمكانية تعديل بيانات البحث الاجتماعي أثناء مرحلة المراجعة"""
    model = SocialResearchForm
    form_class = DigitalSocialResearchForm
    template_name = 'assets_reporting/reviewer/social_research_form.html'
    
    def get_success_url(self):
        return reverse_lazy('aid_management:reviewer_task_list')


# --- 3. قسم اللجنة (المحاضر والتقارير) ---

class CommitteeMeetingListView(LoginRequiredMixin, ListView):
    model = CommitteeMeetingMinute
    template_name = 'assets_reporting/committee/meeting_list.html'
    context_object_name = 'meetings'

class CommitteeMeetingCreateView(LoginRequiredMixin, CreateView):
    model = CommitteeMeetingMinute
    form_class = CommitteeMeetingForm
    template_name = 'assets_reporting/committee/meeting_form.html'
    success_url = reverse_lazy('assets_reporting:meeting_list')

class CommitteeMeetingDetailView(LoginRequiredMixin, DetailView):
    model = CommitteeMeetingMinute
    template_name = 'assets_reporting/committee/meeting_detail.html'
    context_object_name = 'meeting'

class OfficialReportDetailView(LoginRequiredMixin, DetailView):
    model = OfficialReport
    template_name = 'assets_reporting/committee/official_report.html'
    context_object_name = 'report'


# ==========================================
# 3. قسم اللجنة والإدارة (CommitteeHeadRequiredMixin)
# ==========================================

class CommitteeMeetingListView(LoginRequiredMixin, CommitteeHeadRequiredMixin, ListView):
    """سجل بجميع محاضر اجتماعات اللجنة الرسمية"""
    model = CommitteeMeetingMinute
    template_name = 'assets_reporting/committee/meeting_list.html'
    context_object_name = 'meetings'


class CommitteeMeetingCreateView(LoginRequiredMixin, CommitteeHeadRequiredMixin, CreateView):
    """إنشاء محضر اجتماع جديد وتوثيق الطلاب المقبولين فيه"""
    model = CommitteeMeetingMinute
    form_class = CommitteeMeetingForm
    template_name = 'assets_reporting/committee/meeting_form.html'
    success_url = reverse_lazy('assets_reporting:meeting_list')


class CommitteeMeetingDetailView(LoginRequiredMixin, CommitteeHeadRequiredMixin, DetailView):
    """تفاصيل محضر الاجتماع وقائمة الطلاب المشمولين به"""
    model = CommitteeMeetingMinute
    template_name = 'assets_reporting/committee/meeting_detail.html'
    context_object_name = 'meeting'


class OfficialReportListView(LoginRequiredMixin, CommitteeHeadRequiredMixin, ListView):
    """قائمة بكافة التقارير النهائية المؤرشفة في النظام"""
    model = OfficialReport
    template_name = 'assets_reporting/committee/report_list.html'
    context_object_name = 'reports'


class OfficialReportDetailView(LoginRequiredMixin, CommitteeHeadRequiredMixin, DetailView):
    """عرض تقرير رسمي مؤرشف (Snapshot) لضمان عدم التلاعب"""
    model = OfficialReport
    template_name = 'assets_reporting/committee/official_report_view.html'
    context_object_name = 'report'


class VoucherVerifyView(LoginRequiredMixin, CommitteeHeadRequiredMixin, TemplateView):
    """واجهة مخصصة للإدارة أو الخزينة للتحقق من سلامة الباركود والـ Hash للقسيمة"""
    template_name = 'assets_reporting/finance/voucher_verify.html'

    def post(self, request, *args, **kwargs):
        v_number = request.POST.get('v_number')
        hash_to_check = request.POST.get('hash')
        voucher = get_object_or_404(DisbursementVoucher, voucher_number=v_number)
        
        # استدعاء دالة التحقق hmac.compare_digest الموجودة في الموديل
        is_valid = voucher.verify(hash_to_check)
        return render(request, self.template_name, {
            'is_valid': is_valid, 
            'voucher': voucher
        })