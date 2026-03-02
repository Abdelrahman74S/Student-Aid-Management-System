# views/admin_views.py
from django.views.generic import ListView, UpdateView, DeleteView, CreateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Q
from .auth_views import HTMXMixin
from ..models import User, UserRoles, Program, StudentProfile, ReviewerProfile


User = get_user_model()


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == UserRoles.ADMIN and self.request.user.is_superuser
    
    def handle_no_permission(self):
        if self.request.headers.get('HX-Request'):
            return HttpResponse(
                '<div class="text-red-600 p-4">يتطلب صلاحيات المشرف العام</div>',
                status=403
            )
        return super().handle_no_permission()


class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, HTMXMixin, View):

    template_name = 'admin/dashboard.html'
    partial_template_name = 'admin/partials/stats_grid.html'
    
    def get(self, request, *args, **kwargs):
        stats = {
            'total_users': User.objects.count(),
            'total_students': User.objects.filter(role=UserRoles.STUDENT).count(),
            'total_reviewers': User.objects.filter(role=UserRoles.REVIEWER).count(),
            'pending_verifications': User.objects.filter(is_verified=False).count(),
            'programs_count': Program.objects.count(),
            'recent_users': User.objects.order_by('-date_joined')[:5]
        }
        
        return render(request, self.get_template_names()[0], stats)


class UserManagementView(LoginRequiredMixin, AdminRequiredMixin, HTMXMixin, ListView):

    model = User
    template_name = 'admin/user_list.html'
    partial_template_name = 'admin/partials/user_table.html'
    context_object_name = 'users'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = User.objects.annotate(
            student_profile_exists=Count('student_profile'),
            reviewer_profile_exists=Count('reviewer_profile')
        )
        
        role = self.request.GET.get('role', '')
        verified = self.request.GET.get('verified', '')
        search = self.request.GET.get('search', '')
        
        if role:
            queryset = queryset.filter(role=role)
        if verified:
            is_verified = verified == 'true'
            queryset = queryset.filter(is_verified=is_verified)
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(national_id__icontains=search)
            )
        
        return queryset.order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = User.Role.choices
        context['filters'] = {
            'role': self.request.GET.get('role', ''),
            'verified': self.request.GET.get('verified', ''),
            'search': self.request.GET.get('search', '')
        }
        return context
    
    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('HX-Trigger') in ['role-filter', 'verified-filter', 'search']:
            return render(self.request, self.partial_template_name, context)
        return super().render_to_response(context, **response_kwargs)


class UserRoleUpdateView(LoginRequiredMixin, AdminRequiredMixin, View):

    def post(self, request, pk, *args, **kwargs):
        user = get_object_or_404(User, pk=pk)
        new_role = request.POST.get('role')
        
        if new_role not in [r[0] for r in User.Role.choices]:
            return HttpResponse('دور غير صالح', status=400)
        
        old_role = user.role
        user.role = new_role
        user.save()
        
        role_colors = {
            UserRoles.STUDENT: 'bg-blue-100 text-blue-800',
            UserRoles.REVIEWER: 'bg-green-100 text-green-800',
            UserRoles.COMMITTEE_HEAD: 'bg-purple-100 text-purple-800',
            UserRoles.ADMIN: 'bg-red-100 text-red-800',
        }
        
        role_label = dict(User.Role.choices)[new_role]
        
        return HttpResponse(
            f'''
            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full {role_colors.get(new_role, 'bg-gray-100')}">
                {role_label}
            </span>
            ''',
            headers={'HX-Trigger': 'roleChanged'}
        )


class UserVerifyView(LoginRequiredMixin, AdminRequiredMixin, View):

    def post(self, request, pk, *args, **kwargs):
        user = get_object_or_404(User, pk=pk)
        user.is_verified = True
        user.save()
        
        return HttpResponse(
            '''
            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                موثق
            </span>
            ''',
            headers={'HX-Trigger': 'userVerified'}
        )


class ProgramCRUDView(LoginRequiredMixin, AdminRequiredMixin, HTMXMixin, View):
    template_name = 'admin/programs.html'
    partial_template_name = 'admin/partials/program_list.html'
    
    def get(self, request, *args, **kwargs):
        programs = Program.objects.annotate(students_count=Count('students'))
        return render(request, self.get_template_names()[0], {
            'programs': programs,
            'form': None
        })


class BulkActionView(LoginRequiredMixin, AdminRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        user_ids = request.POST.getlist('user_ids[]')
        
        if not user_ids:
            return HttpResponse(
                '<div class="alert alert-warning">لم يتم اختيار مستخدمين</div>',
                status=400
            )
        
        users = User.objects.filter(id__in=user_ids)
        
        if action == 'verify':
            count = users.update(is_verified=True)
            message = f'تم توثيق {count} مستخدم'
        elif action == 'delete':
            count = users.count()
            users.delete()
            message = f'تم حذف {count} مستخدم'
        elif action == 'change_role':
            new_role = request.POST.get('new_role')
            count = users.update(role=new_role)
            message = f'تم تغيير دور {count} مستخدم'
        else:
            return HttpResponse('إجراء غير معروف', status=400)
        
        return HttpResponse(
            f'<div class="alert alert-success">{message}</div>',
            headers={'HX-Trigger': 'bulkActionCompleted'}
        )

class UserDeleteView(LoginRequiredMixin, AdminRequiredMixin, View):
    def delete(self, request, pk, *args, **kwargs):
        user = get_object_or_404(User, pk=pk)
        user.delete()
        return HttpResponse('', status=204)  