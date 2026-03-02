from django.views.generic import View, TemplateView, RedirectView
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordChangeView, 
    PasswordResetView, PasswordResetConfirmView
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.contrib import messages

from ..forms import (
    StudentRegistrationForm, UserLoginForm, UserUpdateForm
)
from ..models import User, UserRoles


class HTMXMixin:
    
    def is_htmx_request(self):
        return self.request.headers.get('HX-Request') == 'true'
    
    def get_template_names(self):
        if self.is_htmx_request():
            return [self.partial_template_name]
        return [self.template_name]


class StudentRegistrationView(HTMXMixin, View):

    template_name = 'accounts/register.html'
    partial_template_name = 'accounts/partials/register_form.html'
    
    def get(self, request, *args, **kwargs):
        form = StudentRegistrationForm()
        return render(request, self.get_template_names()[0], {
            'form': form,
            'title': _('تسجيل حساب جديد')
        })
    
    def post(self, request, *args, **kwargs):
        form = StudentRegistrationForm(request.POST)
        
        if request.headers.get('HX-Trigger-Name') == 'email':
            email = request.POST.get('email', '')
            if User.objects.filter(email__iexact=email).exists():
                return HttpResponse(
                    '<span class="text-red-600 text-sm">⚠️ هذا البريد مسجل مسبقاً</span>',
                    status=200
                )
            return HttpResponse(
                '<span class="text-green-600 text-sm">✓ البريد متاح</span>',
                status=200
            )
        
        if form.is_valid():
            user = form.save(commit=False)
            user.role = UserRoles.STUDENT
            user.save()
            
            if self.is_htmx_request():
                return HttpResponse(
                    f'''
                    <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative" role="alert">
                        <strong class="font-bold">تم التسجيل بنجاح!</strong>
                        <span class="block sm:inline">يمكنك الآن <a href="{reverse_lazy('login')}" class="underline">تسجيل الدخول</a></span>
                    </div>
                    ''',
                    headers={'HX-Redirect': str(reverse_lazy('login'))}
                )
            
            messages.success(request, _('تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول.'))
            return redirect('login')
        
        if self.is_htmx_request():
            return render(request, self.partial_template_name, {
                'form': form,
                'show_errors': True
            })
        
        return render(request, self.template_name, {
            'form': form,
            'title': _('تسجيل حساب جديد')
        })


class CustomLoginView(HTMXMixin, LoginView):

    template_name = 'accounts/login.html'
    partial_template_name = 'accounts/partials/login_form.html'
    form_class = UserLoginForm
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        if self.is_htmx_request():
            return HttpResponse(
                '',
                headers={'HX-Redirect': self.get_success_url()}
            )
        
        messages.success(self.request, _('مرحباً بك، {}!').format(self.request.user.full_name))
        return response
    
    def form_invalid(self, form):
        if self.is_htmx_request():
            return render(self.request, self.partial_template_name, {
                'form': form,
                'error': _('بيانات الدخول غير صحيحة')
            })
        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    next_page = 'login'
    
    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            messages.info(request, _('تم تسجيل الخروج بنجاح.'))
        return super().dispatch(request, *args, **kwargs)


class ProfileUpdateView(LoginRequiredMixin, HTMXMixin, View):

    template_name = 'accounts/profile_edit.html'
    partial_template_name = 'accounts/partials/profile_form.html'
    
    def get(self, request, *args, **kwargs):
        form = UserUpdateForm(instance=request.user)
        return render(request, self.get_template_names()[0], {
            'form': form,
            'user': request.user
        })
    
    def post(self, request, *args, **kwargs):
        form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        
        if form.is_valid():
            form.save()
            
            if self.is_htmx_request():
                return HttpResponse(
                    '''
                    <div class="bg-green-100 border-l-4 border-green-500 text-green-700 p-4 mb-4" role="alert">
                        <p class="font-bold">تم الحفظ!</p>
                        <p>تم تحديث بياناتك بنجاح.</p>
                    </div>
                    ''',
                    headers={'HX-Trigger': 'profileUpdated'}
                )
            
            messages.success(request, _('تم تحديث الملف الشخصي بنجاح.'))
            return redirect('profile_edit')
        
        if self.is_htmx_request():
            return render(request, self.partial_template_name, {'form': form})
        
        return render(request, self.template_name, {
            'form': form,
            'user': request.user
        })


class DashboardRedirectView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        
        if user.role == UserRoles.STUDENT:
            return reverse_lazy('student_dashboard')
        elif user.role == UserRoles.REVIEWER:
            return reverse_lazy('reviewer_dashboard')
        elif user.role == UserRoles.COMMITTEE_HEAD:
            return reverse_lazy('committee_dashboard')
        elif user.role == UserRoles.ADMIN:
            return reverse_lazy('admin_dashboard')
        
        return reverse_lazy('home')