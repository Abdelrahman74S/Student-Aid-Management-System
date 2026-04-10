from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    FormView, ListView, CreateView, UpdateView, 
    DetailView, TemplateView
)

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages

from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Avg, Count
from jsonschema import ValidationError

from .models import (
    SupportCycle, 
    AidApplication, 
    ScoringRule, 
    CommitteeReview, 
    BudgetAllocation
)

from .forms import (
    StudentApplicationForm, 
    CommitteeReviewForm
)

from accounts.models import (
    User, StudentProfile, ReviewerProfile, 
    CommitteeHeadProfile, AuditorProfile
)

from accounts.mixins import (
    StudentRequiredMixin, ReviewerRequiredMixin, 
    CommitteeHeadRequiredMixin, AuditorRequiredMixin
)


# ------------------------- Student Views -------------------------
class StudentApplicationListView(LoginRequiredMixin, StudentRequiredMixin, ListView):
    model = AidApplication
    template_name = "applications/student_application_list.html"
    context_object_name = "applications"

    def get_queryset(self):
        student = self.request.user.studentprofile
        return AidApplication.objects.filter(
            student=student,
            deleted_at__isnull=True
        )

class StudentApplicationCreateView(LoginRequiredMixin, StudentRequiredMixin, CreateView):
    model = AidApplication
    form_class = StudentApplicationForm
    template_name = "applications/student_application_form.html"

    def dispatch(self, request, *args, **kwargs):
        cycle = SupportCycle.objects.filter(status='OPEN').first()

        if not cycle or not cycle.is_open_for_application:
            messages.error(request, "التقديم غير متاح حالياً")
            return redirect('student_application_list')

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.student = self.request.user.studentprofile
        form.instance.cycle = SupportCycle.objects.filter(status='OPEN').first()
        messages.success(self.request, "تم إنشاء الطلب كمسودة")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('student_application_list')

class StudentApplicationUpdateView(LoginRequiredMixin, StudentRequiredMixin, UpdateView):
    model = AidApplication
    form_class = StudentApplicationForm
    template_name = "applications/student_application_form.html"

    def get_object(self):
        obj = get_object_or_404(
            AidApplication,
            id=self.kwargs['pk'],
            student=self.request.user.studentprofile
        )

        if obj.status != 'DRAFT':
            raise ValidationError("لا يمكن تعديل طلب بعد الإرسال")

        return obj

    def form_valid(self, form):
        messages.success(self.request, "تم تعديل الطلب")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('student_application_list')

class StudentApplicationDetailView(LoginRequiredMixin, StudentRequiredMixin, DetailView):
    model = AidApplication
    template_name = "applications/student_application_detail.html"
    context_object_name = "application"

    def get_object(self):
        return get_object_or_404(
            AidApplication,
            id=self.kwargs['pk'],
            student=self.request.user.studentprofile
        )

class StudentApplicationSubmitView(LoginRequiredMixin, StudentRequiredMixin, View):
    def post(self, request, pk):
        app = get_object_or_404(
            AidApplication,
            id=pk,
            student=request.user.studentprofile
        )

        try:
            app.submit(request=request)
            messages.success(request, "تم إرسال الطلب بنجاح")
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('student_application_detail', pk=pk)

# ------------------------- Reviewer Views -------------------------
class ReviewerTaskListView(LoginRequiredMixin, ReviewerRequiredMixin, ListView):
    model = AidApplication
    template_name = 'reviewer/task_list.html'
    context_object_name = 'tasks'

    def get_queryset(self):
        return AidApplication.objects.filter(
            status='UNDER_REVIEW'
        ).select_related('student__user')

class ApplicationScoringView(LoginRequiredMixin, ReviewerRequiredMixin, CreateView):
    model = CommitteeReview
    form_class = CommitteeReviewForm
    template_name = 'reviewer/application_scoring.html'
    success_url = reverse_lazy('reviewer:task_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        application = get_object_or_404(AidApplication, id=self.kwargs['pk'])
        kwargs['application'] = application
        return kwargs

    def form_valid(self, form):
        form.instance.reviewer = self.request.user
        form.instance.application_id = self.kwargs['pk']
        
        messages.success(self.request, "تم حفظ التقييم بنجاح.")
        return super().form_valid(form)

class ReviewConflictFlagView(LoginRequiredMixin, ReviewerRequiredMixin, FormView):
    template_name = 'reviewer/conflict_report.html'
    success_url = reverse_lazy('reviewer:task_list')

    def form_valid(self, form):
        application = get_object_or_404(AidApplication, id=self.kwargs['pk'])
        
        CommitteeReview.objects.create(
            application=application,
            reviewer=self.request.user,
            conflict_of_interest=True,
            notes=form.cleaned_data.get('reason', 'تضارب مصالح')
        )

        messages.warning(self.request, "تم الإبلاغ عن تضارب المصالح بنجاح.")
        return super().form_valid(form)

# ------------------------- Committee Head Views -------------------------

# -------------------------  Views -------------------------

@transaction.atomic
def some_budget_update_view(request):
    cycle_id = request.POST.get('cycle_id')
    amount = float(request.POST.get('amount'))

    cycle = SupportCycle.objects.select_for_update().get(id=cycle_id)

    if cycle.available_budget < amount:
        return JsonResponse({'error': 'Insufficient budget'}, status=400)

    BudgetAllocation.objects.create(
        cycle=cycle,
        amount_allocated=amount,
        status='PENDING'
    )

    cycle.reserved_budget += amount
    cycle.available_budget -= amount
    cycle.save(update_fields=['reserved_budget', 'available_budget'])

    return JsonResponse({'message': 'Success'})