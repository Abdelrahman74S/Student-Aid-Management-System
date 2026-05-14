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
    CommitteeMeetingMinute, DisbursementVoucher, OfficialReport, SystemTemplate
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

    def get_queryset(self):
        return ApplicationDocument.objects.filter(application__student__user=self.request.user)


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

from accounts.mixins import ReviewerProgramRequiredMixin

class SocialResearchCreateView(LoginRequiredMixin, ReviewerProgramRequiredMixin, CreateView):
    """واجهة للباحث لملء استمارة البحث الاجتماعي الرقمية"""
    model = SocialResearchForm
    form_class = DigitalSocialResearchForm
    template_name = 'assets_reporting/reviewer/social_research_form.html'

    def get_object(self, queryset=None):
        # ميكسين ReviewerProgramRequiredMixin يتوقع get_object ليرجع الطلب
        return get_object_or_404(AidApplication, pk=self.kwargs.get('app_id'))

    def form_valid(self, form):
        form.instance.application = self.get_object()
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('aid_management:reviewer_task_list')


class SocialResearchUpdateView(LoginRequiredMixin, ReviewerProgramRequiredMixin, UpdateView):
    """إمكانية تعديل بيانات البحث الاجتماعي أثناء مرحلة المراجعة"""
    model = SocialResearchForm
    form_class = DigitalSocialResearchForm
    template_name = 'assets_reporting/reviewer/social_research_form.html'
    
    def get_object(self, queryset=None):
        return get_object_or_404(SocialResearchForm, pk=self.kwargs.get('pk'))

    def dispatch(self, request, *args, **kwargs):
        # تحقق إضافي للـ UpdateView
        obj = self.get_object()
        if not request.user.reviewer_profile.assigned_programs.filter(id=obj.application.student.program_id).exists():
            from django.contrib import messages
            messages.error(request, "ليس لديك صلاحية لتعديل بحث هذا الطالب.")
            return redirect('accounts:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('aid_management:reviewer_task_list')


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

from django.http import FileResponse, Http404
from django.views import View

class DownloadTemplatesView(LoginRequiredMixin, ListView):
    """واجهة تتيح للمستخدمين تنزيل النماذج بناءً على أدوارهم (صلاحياتهم)"""
    model = SystemTemplate
    template_name = 'assets_reporting/system_templates_list.html'
    context_object_name = 'templates'

    def get_queryset(self):
        user = self.request.user
        if user.role == 'A' or user.is_superuser:
            return SystemTemplate.objects.all()
        return SystemTemplate.objects.filter(role_required=user.role)

class SecureTemplateDownloadView(LoginRequiredMixin, View):
    """تحميل الملفات بشكل آمن مع التحقق من الصلاحيات لكل دور"""
    def get(self, request, pk):
        template = get_object_or_404(SystemTemplate, pk=pk)
        
        # السماح بالتحميل فقط إذا كان الدور مطابقاً أو كان المستخدم مديراً
        if template.role_required != request.user.role and request.user.role != 'A':
            from django.contrib import messages
            messages.error(request, "ليس لديك صلاحية لتحميل هذا النموذج.")
            return redirect('assets_reporting:template_list')
        
        if not template.file:
            raise Http404("الملف غير موجود.")
            
        return FileResponse(template.file, as_attachment=True)