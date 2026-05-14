from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, View, CreateView, DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .models import Notification, Appeal
from accounts.mixins import StudentRequiredMixin, CommitteeHeadRequiredMixin


# ==========================================
# 1. الإشعارات (جميع المستخدمين)
# ==========================================

class NotificationListView(LoginRequiredMixin, ListView):
    """قائمة إشعارات المستخدم الحالي."""
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = Notification.objects.filter(
            recipient=self.request.user, is_read=False
        ).count()
        return context


class NotificationMarkReadView(LoginRequiredMixin, View):
    """تعليم إشعار كمقروء."""
    def post(self, request, pk):
        notification = get_object_or_404(
            Notification, pk=pk, recipient=request.user
        )
        notification.mark_as_read()

        if notification.related_url:
            return redirect(notification.related_url)
        return redirect('notifications:list')


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    """تعليم جميع الإشعارات كمقروءة."""
    def post(self, request):
        Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)
        messages.success(request, _("تم تعليم جميع الإشعارات كمقروءة."))
        return redirect('notifications:list')


class UnreadCountAPIView(LoginRequiredMixin, View):
    """API بسيط لإرجاع عدد الإشعارات غير المقروءة (لتحديث الـ badge)."""
    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return JsonResponse({'unread_count': count})


# ==========================================
# 2. التظلمات — واجهة الطالب
# ==========================================

class AppealCreateView(LoginRequiredMixin, StudentRequiredMixin, CreateView):
    """تقديم تظلم على طلب مرفوض."""
    model = Appeal
    fields = ['reason', 'supporting_documents']
    template_name = 'notifications/appeal_form.html'
    success_url = reverse_lazy('notifications:appeal_list')

    def dispatch(self, request, *args, **kwargs):
        from aid_management.models import AidApplication
        self.application = get_object_or_404(
            AidApplication,
            pk=kwargs['app_id'],
            student__user=request.user,
        )
        if self.application.status != 'REJECTED':
            messages.error(request, _("لا يمكن تقديم تظلم إلا على طلب مرفوض."))
            return redirect('aid_management:application_list')
        # التحقق من عدم وجود تظلم نشط بالفعل
        if Appeal.objects.filter(
            application=self.application,
            student=request.user,
            status__in=['PENDING', 'UNDER_REVIEW'],
        ).exists():
            messages.warning(request, _("لديك تظلم قائم بالفعل على هذا الطلب."))
            return redirect('notifications:appeal_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.application = self.application
        form.instance.student = self.request.user
        messages.success(self.request, _("تم تقديم التظلم بنجاح. سيتم مراجعته من اللجنة."))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['application'] = self.application
        return context


class AppealListView(LoginRequiredMixin, StudentRequiredMixin, ListView):
    """قائمة تظلمات الطالب."""
    model = Appeal
    template_name = 'notifications/appeal_list.html'
    context_object_name = 'appeals'

    def get_queryset(self):
        return Appeal.objects.filter(student=self.request.user)


# ==========================================
# 3. التظلمات — واجهة اللجنة
# ==========================================

class AppealReviewListView(LoginRequiredMixin, CommitteeHeadRequiredMixin, ListView):
    """قائمة التظلمات المعلقة للجنة."""
    model = Appeal
    template_name = 'notifications/appeal_review_list.html'
    context_object_name = 'appeals'

    def get_queryset(self):
        return Appeal.objects.filter(
            status__in=['PENDING', 'UNDER_REVIEW']
        ).select_related('student', 'application', 'application__cycle')


class AppealReviewUpdateView(LoginRequiredMixin, CommitteeHeadRequiredMixin, UpdateView):
    """مراجعة وتحديث حالة التظلم من اللجنة."""
    model = Appeal
    fields = ['status', 'admin_response']
    template_name = 'notifications/appeal_review_form.html'
    success_url = reverse_lazy('notifications:appeal_review_list')

    def form_valid(self, form):
        form.instance.reviewed_by = self.request.user

        # إشعار الطالب
        from .services import notify_appeal_status_change
        response = super().form_valid(form)
        notify_appeal_status_change(self.object)

        # إذا تم قبول التظلم، إعادة الطلب لمرحلة DRAFT
        if self.object.status == 'ACCEPTED':
            application = self.object.application
            if application.status == 'REJECTED':
                application.status = 'DRAFT'
                application.save(update_fields=['status', 'updated_at'])
                messages.success(self.request, _("تم قبول التظلم وإعادة الطلب لمرحلة المسودة."))
        else:
            messages.info(self.request, _("تم تحديث حالة التظلم."))

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['application'] = self.object.application
        return context
