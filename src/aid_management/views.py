from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import (
    FormView, ListView, CreateView, UpdateView, 
    DetailView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Avg, Count, Q
from django.core.exceptions import ValidationError

from .models import (
    SupportCycle, AidApplication, ScoringRule, 
    CommitteeReview, BudgetAllocation
)
from .forms import StudentApplicationForm, CommitteeReviewForm, ApplicationDocumentFormSet
from accounts.models import User, StudentProfile, ReviewerProfile
from accounts.mixins import (
    StudentRequiredMixin, ReviewerRequiredMixin, 
    CommitteeHeadRequiredMixin
)

# =================================================================
# 1. Student Portal – محمود
# =================================================================

class StudentApplicationListView(LoginRequiredMixin, StudentRequiredMixin, ListView):
    model = AidApplication
    template_name = "aid_management/student/application_list.html"
    context_object_name = "applications"

    def get_queryset(self):
        return AidApplication.objects.filter(
            student=self.request.user.student_profile,
            deleted_at__isnull=True
        ).select_related('cycle')


class StudentApplicationCreateView(LoginRequiredMixin, StudentRequiredMixin, CreateView):
    model = AidApplication
    form_class = StudentApplicationForm
    template_name = "aid_management/student/application_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.active_cycle = SupportCycle.objects.filter(status='OPEN').first()
        if not self.active_cycle or not self.active_cycle.is_open_for_application:
            messages.error(request, "لا توجد دورة دعم متاحة للتقديم حالياً.")
            return redirect('aid_management:application_list')

        if AidApplication.objects.filter(
            student=request.user.student_profile,
            cycle=self.active_cycle
        ).exists():
            messages.warning(request, "لقد قمت بالتقديم بالفعل في هذه الدورة.")
            return redirect('aid_management:application_list')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = ApplicationDocumentFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context['formset'] = ApplicationDocumentFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        form.instance.student = self.request.user.student_profile
        form.instance.cycle = self.active_cycle
        
        if form.is_valid() and formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, "تم حفظ المسودة بنجاح.")
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('aid_management:application_list')


class StudentApplicationUpdateView(LoginRequiredMixin, StudentRequiredMixin, UpdateView):
    model = AidApplication
    form_class = StudentApplicationForm
    template_name = "aid_management/student/application_form.html"

    def get_queryset(self):
        return AidApplication.objects.filter(
            student=self.request.user.student_profile,
            status='DRAFT'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = ApplicationDocumentFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context['formset'] = ApplicationDocumentFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        if form.is_valid() and formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, "تم تحديث المسودة بنجاح.")
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('aid_management:application_list')

class StudentApplicationSubmitView(LoginRequiredMixin, StudentRequiredMixin, View):
    def post(self, request, pk):
        application = get_object_or_404(
            AidApplication,
            id=pk,
            student=request.user.student_profile
        )

        try:
            with transaction.atomic():
                application.freeze_student_data()
                application.submit(request=request)

            messages.success(request, "تم إرسال الطلب بنجاح.")
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('aid_management:application_detail', pk=pk)


class StudentApplicationWithdrawView(LoginRequiredMixin, StudentRequiredMixin, View):
    def post(self, request, pk):
        application = get_object_or_404(
            AidApplication,
            id=pk,
            student=request.user.student_profile
        )

        try:
            application.soft_delete()
            messages.info(request, "تم سحب الطلب بنجاح.")
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('aid_management:application_list')


class StudentApplicationDetailView(LoginRequiredMixin, StudentRequiredMixin, DetailView):
    model = AidApplication
    template_name = "aid_management/student/application_detail.html"
    context_object_name = "application"

    def get_queryset(self):
        return AidApplication.objects.filter(
            student=self.request.user.student_profile
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_object()

        if application.status in ['SCORED', 'APPROVED', 'REJECTED', 'DISBURSED']:
            context['reviews_summary'] = application.reviews.filter(
                is_submitted=True
            ).aggregate(
                avg_total=Avg('total_score'),
                count=Count('id')
            )

        if application.status in ['APPROVED', 'DISBURSED']:
            context['allocation'] = application.allocations.filter(
                status__in=['PENDING', 'DISBURSED']
            ).first()

        context['timeline'] = self.get_application_timeline(application)
        return context

    def get_application_timeline(self, app):
        events = []
        events.append({'label': 'إنشاء المسودة', 'date': app.created_at, 'status': 'completed'})

        if app.submission_date:
            events.append({'label': 'تم تقديم الطلب', 'date': app.submission_date, 'status': 'completed'})

        if app.status == 'UNDER_REVIEW':
            events.append({'label': 'قيد المراجعة', 'date': None, 'status': 'active'})

        if app.decision_date:
            label = 'تم القبول' if app.status in ['APPROVED', 'DISBURSED'] else 'تم الرفض'
            events.append({'label': label, 'date': app.decision_date, 'status': 'completed'})

        return events


# =================================================================
# 2. Reviewer System – ياسمين
# =================================================================

class ReviewerTaskListView(LoginRequiredMixin, ReviewerRequiredMixin, ListView):
    template_name = "aid_management/reviewer/task_list.html"
    context_object_name = "reviews"

    def get_queryset(self):
        return CommitteeReview.objects.filter(
            reviewer=self.request.user,
            is_submitted=False
        ).select_related('application__student__user', 'application__cycle')


class ApplicationScoringView(LoginRequiredMixin, ReviewerRequiredMixin, UpdateView):
    model = CommitteeReview
    form_class = CommitteeReviewForm
    template_name = "aid_management/reviewer/scoring.html"

    def get_queryset(self):
        return CommitteeReview.objects.filter(reviewer=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['application'] = self.get_object().application
        return kwargs

    def form_valid(self, form):
        review = form.save(commit=False)

        if 'submit_final' in self.request.POST:
            try:
                review.submit()
                messages.success(self.request, "تم اعتماد التقييم نهائياً.")
            except ValidationError as e:
                messages.error(self.request, str(e))
                return self.form_invalid(form)
        else:
            review.save()
            messages.info(self.request, "تم حفظ كمسودة.")

        return redirect('aid_management:reviewer_task_list')


class ReviewConflictFlagView(LoginRequiredMixin, ReviewerRequiredMixin, View):
    def post(self, request, pk):
        review = get_object_or_404(CommitteeReview, id=pk, reviewer=request.user)
        review.conflict_of_interest = True
        review.qualitative_notes = request.POST.get('reason', 'تعارض مصالح')
        review.save()
        messages.warning(request, "تم الإبلاغ عن تعارض مصالح.")
        return redirect('aid_management:reviewer_task_list')


# =================================================================
# 3. Committee – كريم
# =================================================================

class CommitteeHeadDashboardView(LoginRequiredMixin, CommitteeHeadRequiredMixin, TemplateView):
    template_name = "aid_management/committee/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cycle = SupportCycle.objects.filter(status__in=['OPEN', 'UNDER_REVIEW']).first()

        if cycle:
            context['cycle'] = cycle
            context['total_apps'] = cycle.applications.count()
            context['submitted_reviews'] = CommitteeReview.objects.filter(
                application__cycle=cycle, is_submitted=True
            ).count()
            context['budget_usage'] = (cycle.reserved_budget / cycle.total_budget * 100 
                                      if cycle.total_budget else 0)
        return context


class ApplicationRankListView(LoginRequiredMixin, CommitteeHeadRequiredMixin, ListView):
    template_name = "aid_management/committee/ranking_list.html"
    context_object_name = "ranked_applications"

    def get_queryset(self):
        cycle_id = self.request.GET.get('cycle')
        managed_programs = self.request.user.committee_head_profile.managed_programs.all()
        qs = AidApplication.objects.filter(status='SCORED', student__program__in=managed_programs)
        if cycle_id:
            qs = qs.filter(cycle_id=cycle_id)
        return qs.annotate(avg_score=Avg('reviews__total_score')).order_by('-avg_score')


class FinalDecisionUpdateView(LoginRequiredMixin, CommitteeHeadRequiredMixin, View):
    def post(self, request, pk):
        managed_programs = request.user.committee_head_profile.managed_programs.all()
        application = get_object_or_404(AidApplication, id=pk, student__program__in=managed_programs)
        decision = request.POST.get('decision')
        amount = request.POST.get('amount', 0)

        try:
            with transaction.atomic():
                application.status = decision
                application.committee_decision = request.POST.get('notes')
                application.decision_date = timezone.now()
                application.save()

                if decision == 'APPROVED':
                    BudgetAllocation.objects.create(
                        cycle=application.cycle,
                        application=application,
                        amount_allocated=amount
                    )
            messages.success(request, f"تم تحديث القرار للطلب {application.serial_number}")
        except Exception as e:
            messages.error(request, f"خطأ: {str(e)}")
        return redirect('aid_management:application_rank_list')


class AutomatedDistributionView(LoginRequiredMixin, CommitteeHeadRequiredMixin, View):
    def post(self, request):
        cycle = SupportCycle.objects.filter(status='UNDER_REVIEW').first()
        reviewers = User.objects.filter(groups__name='Reviewers')
        applications = AidApplication.objects.filter(cycle=cycle, status='SUBMITTED')

        created_count = 0
        with transaction.atomic():
            for app in applications:
                for rev in reviewers[:2]:
                    CommitteeReview.objects.get_or_create(application=app, reviewer=rev)
                app.status = 'UNDER_REVIEW'
                app.save()
                created_count += 1
        messages.success(request, f"تم توزيع {created_count} طلب على المراجعين.")
        return redirect('aid_management:committee_dashboard')


class CycleStatusTransitionView(LoginRequiredMixin, CommitteeHeadRequiredMixin, View):
    def post(self, request, pk):
        cycle = get_object_or_404(SupportCycle, id=pk)
        new_status = request.POST.get('status')
        valid_statuses = [c[0] for c in SupportCycle.STATUS_CHOICES]

        if new_status not in valid_statuses:
            messages.error(request, "حالة غير صالحة.")
            return redirect('aid_management:committee_dashboard')

        cycle_flow = {
            'DRAFT': ['OPEN'],
            'OPEN': ['UNDER_REVIEW', 'CLOSED'],
            'UNDER_REVIEW': ['CLOSED'],
            'CLOSED': ['ARCHIVED']
        }

        if new_status not in cycle_flow.get(cycle.status, []):
            messages.error(request, "انتقال غير منطقي.")
            return redirect('aid_management:committee_dashboard')

        try:
            with transaction.atomic():
                if new_status == 'OPEN':
                    if not cycle.rules.exists():
                        raise ValidationError("يجب إضافة قواعد التقييم أولاً.")
                    cycle.scoring_rules_snapshot = list(
                        cycle.rules.values('criteria_type', 'points', 'weight')
                    )
                elif new_status == 'CLOSED':
                    cycle.is_locked = True

                cycle.status = new_status
                cycle.save()
            messages.success(request, f"تم تغيير الحالة إلى {cycle.get_status_display()}")
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, str(e))
        return redirect('aid_management:committee_dashboard')