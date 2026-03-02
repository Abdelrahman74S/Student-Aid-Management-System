# views/reviewer_views.py
from django.views.generic import ListView, DetailView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from .auth_views import HTMXMixin
from ..models import UserRoles, ReviewerProfile, StudentProfile, Program
from ..forms import ReviewerProfileForm


class ReviewerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == UserRoles.REVIEWER
    
    def handle_no_permission(self):
        if self.request.headers.get('HX-Request'):
            return HttpResponse(
                '<div class="alert alert-error">غير مصرح لك</div>',
                status=403
            )
        return super().handle_no_permission()


class ReviewerDashboardView(LoginRequiredMixin, ReviewerRequiredMixin, HTMXMixin, View):
    template_name = 'reviewers/dashboard.html'
    partial_template_name = 'reviewers/partials/dashboard_stats.html'
    
    def get(self, request, *args, **kwargs):
        profile = get_object_or_404(ReviewerProfile, user=request.user)
        
        assigned_programs = profile.assigned_programs.all()
        total_students = StudentProfile.objects.filter(
            program__in=assigned_programs
        ).count()
        
        context = {
            'profile': profile,
            'assigned_programs': assigned_programs,
            'total_students': total_students,
        }
        
        return render(request, self.get_template_names()[0], context)


class ReviewerProfileUpdateView(LoginRequiredMixin, ReviewerRequiredMixin, HTMXMixin, UpdateView):

    model = ReviewerProfile
    form_class = ReviewerProfileForm
    template_name = 'reviewers/profile_edit.html'
    partial_template_name = 'reviewers/partials/profile_form.html'
    success_url = reverse_lazy('reviewer_dashboard')
    
    def get_object(self):
        return get_object_or_404(ReviewerProfile, user=self.request.user)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        if self.is_htmx_request():
            return HttpResponse(
                '<div class="toast toast-success">تم تحديث البيانات</div>',
                headers={'HX-Trigger': 'profileUpdated'}
            )
        return response


class AssignedStudentsView(LoginRequiredMixin, ReviewerRequiredMixin, HTMXMixin, ListView):
    model = StudentProfile
    template_name = 'reviewers/student_list.html'
    partial_template_name = 'reviewers/partials/student_table.html'
    context_object_name = 'students'
    paginate_by = 25
    
    def get_queryset(self):
        profile = get_object_or_404(ReviewerProfile, user=self.request.user)
        queryset = StudentProfile.objects.filter(
            program__in=profile.assigned_programs.all()
        ).select_related('user', 'program')
        
        program_filter = self.request.GET.get('program')
        if program_filter:
            queryset = queryset.filter(program_id=program_filter)
        
        level = self.request.GET.get('level')
        if level:
            queryset = queryset.filter(level=level)
        
        return queryset.order_by('program__name', 'user__full_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = get_object_or_404(ReviewerProfile, user=self.request.user)
        context['assigned_programs'] = profile.assigned_programs.all()
        context['levels'] = StudentProfile.Level.choices
        return context
    
    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('HX-Trigger') in ['program-filter', 'level-filter']:
            return render(self.request, self.partial_template_name, context)
        return super().render_to_response(context, **response_kwargs)


class QuickStudentApproveView(LoginRequiredMixin, ReviewerRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        student = get_object_or_404(StudentProfile, pk=pk)
        profile = get_object_or_404(ReviewerProfile, user=request.user)
        
        if student.program not in profile.assigned_programs.all():
            return HttpResponse(
                '<span class="text-red-600">غير مصرح</span>',
                status=403
            )
        
        return HttpResponse(
            f'''
            <button class="btn btn-success btn-sm" disabled>
                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
                تمت الموافقة
            </button>
            ''',
            headers={'HX-Trigger': 'studentApproved'}
        )