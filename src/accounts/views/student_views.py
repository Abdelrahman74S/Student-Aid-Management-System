from django.views.generic import (
    DetailView, UpdateView, ListView, CreateView, DeleteView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from .auth_views import HTMXMixin
from ..models import UserRoles, StudentProfile, Program
from ..forms import StudentProfileForm


class StudentRequiredMixin(UserPassesTestMixin):    
    def test_func(self):
        return self.request.user.role == UserRoles.STUDENT
    
    def handle_no_permission(self):
        if self.request.headers.get('HX-Request'):
            return HttpResponse(
                '<div class="text-red-600 p-4">غير مصرح لك بالوصول لهذه الصفحة</div>',
                status=403
            )
        return super().handle_no_permission()


class StudentDashboardView(LoginRequiredMixin, StudentRequiredMixin, HTMXMixin, DetailView):
    template_name = 'students/dashboard.html'
    partial_template_name = 'students/partials/dashboard_content.html'
    context_object_name = 'profile'
    
    def get_object(self):
        return get_object_or_404(StudentProfile, user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['academic_standing'] = self.object.academic_standing
        context['recent_activities'] = []  # يمكن إضافة النشاطات هنا
        return context


class StudentProfileUpdateView(LoginRequiredMixin, StudentRequiredMixin, HTMXMixin, UpdateView):
    model = StudentProfile
    form_class = StudentProfileForm
    template_name = 'students/profile_edit.html'
    partial_template_name = 'students/partials/profile_form.html'
    success_url = reverse_lazy('student_dashboard')
    
    def get_object(self):
        return get_object_or_404(StudentProfile, user=self.request.user)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        if self.is_htmx_request():
            return HttpResponse(
                '''
                <div class="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
                    <div class="flex">
                        <div class="flex-shrink-0">
                            <svg class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                            </svg>
                        </div>
                        <div class="mr-3">
                            <p class="text-sm leading-5 font-medium text-green-800">
                                تم حفظ البيانات بنجاح
                            </p>
                        </div>
                    </div>
                </div>
                ''',
                headers={'HX-Trigger': 'profileSaved'}
            )
        
        return response
    
    def form_invalid(self, form):
        if self.is_htmx_request():
            return render(self.request, self.partial_template_name, {
                'form': form,
                'errors': form.errors
            })
        return super().form_invalid(form)


class ProgramListView(LoginRequiredMixin, HTMXMixin, ListView):
    model = Program
    template_name = 'students/program_list.html'
    partial_template_name = 'students/partials/program_list.html'
    context_object_name = 'programs'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Program.objects.filter(is_active=True)
        search = self.request.GET.get('search', '')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('name')
    
    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('HX-Trigger-Name') == 'search':
            return render(self.request, 'students/partials/program_items.html', context)
        return super().render_to_response(context, **response_kwargs)


class StudentSearchView(LoginRequiredMixin, HTMXMixin, ListView):
    model = StudentProfile
    template_name = 'students/student_search.html'
    partial_template_name = 'students/partials/search_results.html'
    context_object_name = 'students'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = StudentProfile.objects.select_related('user', 'program')
        
        q = self.request.GET.get('q', '')
        program = self.request.GET.get('program', '')
        level = self.request.GET.get('level', '')
        
        if q:
            queryset = queryset.filter(
                Q(user__full_name__icontains=q) |
                Q(student_id__icontains=q) |
                Q(user__email__icontains=q) |
                Q(user__national_id__icontains=q)
            )
        
        if program:
            queryset = queryset.filter(program_id=program)
        
        if level:
            queryset = queryset.filter(level=level)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['programs'] = Program.objects.filter(is_active=True)
        context['levels'] = StudentProfile.Level.choices
        return context