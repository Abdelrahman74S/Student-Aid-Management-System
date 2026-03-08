import uuid
from django.shortcuts import render, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import View, CreateView, TemplateView, FormView
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.views import  PasswordResetView, PasswordResetConfirmView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.http import  HttpResponse
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm
from django.template.loader import render_to_string
from django.contrib.auth import update_session_auth_hash
from django.utils.translation import gettext_lazy as _


from ..models import User, StudentProfile
from ..forms import RegistrationForm, UserLoginForm
from ..tokens import email_verification_token


class HTMXMixin:
    """Mixin to handle HTMX requests"""
    def is_htmx(self, request):
        return request.headers.get('HX-Request') == 'true'
    
    def htmx_response(self, template_name, context=None, **kwargs):
        """Return partial template for HTMX, full page otherwise"""
        context = context or {}
        if self.request.headers.get('HX-Request') == 'true':
            # Return only the form partial for HTMX
            return render(self.request, f"accounts/partials/{template_name}", context, **kwargs)
        # Return full page
        return render(self.request, f"accounts/{template_name}", context, **kwargs)
    
    def htmx_redirect(self, url):
        """Handle redirect for HTMX"""
        if self.request.headers.get('HX-Request') == 'true':
            response = HttpResponse()
            response['HX-Redirect'] = url
            return response
        return redirect(url)
    
    def htmx_trigger(self, event_name, data=None):
        """Trigger HTMX event"""
        response = HttpResponse()
        response['HX-Trigger'] = event_name
        if data:
            response['HX-Trigger-Data'] = data
        return response


class RegisterView(HTMXMixin, CreateView):
    """Student registration with university email - HTMX enabled"""
    model = User
    form_class = RegistrationForm
    template_name = 'register.html'
    success_url = reverse_lazy('accounts:login')
    
    def get(self, request, *args, **kwargs):
        # If user is already authenticated, redirect to dashboard
        if request.user.is_authenticated:
            return self.htmx_redirect(reverse('accounts:dashboard'))
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_htmx'] = self.is_htmx(self.request)
        return context
    
    def form_valid(self, form):
        user = form.save(commit=False)
        user.role = User.Role.STUDENT
        user.is_active = True  
        user.is_verified = False
        user.save()
        
        # Create empty student profile
        StudentProfile.objects.create(user=user)
        
        # Send verification email
        self.send_verification_email(user)
        
        success_message = (
            "تم إنشاء الحساب بنجاح! "
            "يرجى التحقق من بريدك الإلكتروني لتفعيل الحساب."
        )
        
        if self.is_htmx(self.request):
            # Return success message that swaps the form
            return render(self.request, 'accounts/partials/register_success.html', {
                'message': success_message,
                'email': user.email
            })
        
        messages.success(self.request, success_message)
        return redirect(self.success_url)
    
    def form_invalid(self, form):
        if self.is_htmx(self.request):
            # Return form with errors for HTMX to swap
            return render(self.request, 'accounts/partials/register_form.html', {
                'form': form,
                'is_htmx': True
            }, status=422)
        return super().form_invalid(form)
    
    def send_verification_email(self, user):
        token = email_verification_token.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        current_site = get_current_site(self.request)
        verification_url = reverse('accounts:verify_email', kwargs={
            'token': f"{uid}-{token}"
        })
        
        full_url = f"https://{current_site.domain}{verification_url}"
        
        subject = 'تفعيل حسابك - نظام المساعدات الطلابية'
        message = render_to_string('accounts/emails/verification_email.html', {
            'user': user,
            'verification_url': full_url,
        })
        
        send_mail(
            subject=subject,
            message='',
            html_message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


class UserLoginView(HTMXMixin, FormView):
    """Custom login with email - HTMX enabled"""
    template_name = 'login.html'
    form_class = UserLoginForm
    
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return self.htmx_redirect(reverse('accounts:dashboard'))
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_htmx'] = self.is_htmx(self.request)
        return context
    
    def form_valid(self, form):
        email = form.cleaned_data.get('username')  # Using email as username
        password = form.cleaned_data.get('password')
        
        user = authenticate(self.request, username=email, password=password)
        
        if user is not None:
            if not user.is_active:
                error_msg = "الحساب معطل. يرجى التواصل مع الإدارة."
                return self._handle_error(error_msg)
            
            login(self.request, user)
            
            # Determine redirect URL
            next_url = self.request.POST.get('next') or self.request.GET.get('next')
            if next_url:
                redirect_url = next_url
            else:
                redirect_url = reverse('accounts:dashboard')
            
            return self.htmx_redirect(redirect_url)
        
        error_msg = "البريد الإلكتروني أو كلمة المرور غير صحيحة."
        return self._handle_error(error_msg)
    
    def _handle_error(self, error_message):
        if self.is_htmx(self.request):
            return render(self.request, 'accounts/partials/login_form.html', {
                'form': self.form_class(self.request.POST),
                'error': error_message,
                'is_htmx': True
            }, status=401)
        
        messages.error(self.request, error_message)
        return self.render_to_response(self.get_context_data(form=self.form_class(self.request.POST)))
    
    def form_invalid(self, form):
        if self.is_htmx(self.request):
            return render(self.request, 'accounts/partials/login_form.html', {
                'form': form,
                'is_htmx': True
            }, status=422)
        return super().form_invalid(form)


class UserLogoutView(View):
    """Logout and redirect - works with HTMX"""
    
    def post(self, request, *args, **kwargs):
        logout(request)
        
        # Check if HTMX request
        if request.headers.get('HX-Request') == 'true':
            response = HttpResponse()
            response['HX-Redirect'] = reverse('accounts:login')
            response['HX-Trigger'] = 'userLoggedOut'
            return response
        
        messages.success(request, "تم تسجيل الخروج بنجاح.")
        return redirect('accounts:login')
    
    def get(self, request, *args, **kwargs):
        # Allow GET for HTMX or redirect to POST
        if request.headers.get('HX-Request') == 'true':
            return self.post(request, *args, **kwargs)
        return redirect('accounts:login')


class EmailVerificationView(View):
    """Verify email via token - HTMX enabled"""
    template_name = 'verification_result.html'
    
    def get(self, request, token, *args, **kwargs):
        try:
            # Token format: uid-token
            uidb64, token_key = token.split('-', 1)
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (ValueError, TypeError, OverflowError, User.DoesNotExist):
            user = None
        
        context = {}
        
        if user is not None and email_verification_token.check_token(user, token_key):
            if not user.is_verified:
                user.is_verified = True
                user.save()
                context['success'] = True
                context['message'] = "تم تفعيل حسابك بنجاح! يمكنك الآن تسجيل الدخول."
            else:
                context['success'] = True
                context['message'] = "الحساب مفعل مسبقاً."
        else:
            context['success'] = False
            context['message'] = "رابط التفعيل غير صالح أو منتهي الصلاحية."
        
        # Check for HTMX
        if request.headers.get('HX-Request') == 'true':
            return render(request, 'accounts/partials/verification_result.html', context)
        
        return render(request, self.template_name, context)


class ResendVerificationEmailView(HTMXMixin, View):
    """Resend verification email - HTMX enabled"""
    
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email', '').strip().upper()
        
        try:
            user = User.objects.get(email=email, is_verified=False)
            self.send_verification_email(user)
            message = "تم إرسال رابط التفعيل الجديد إلى بريدك الإلكتروني."
            success = True
        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            message = "إذا كان البريد الإلكتروني مسجلاً وغير مفعل، فسيتم إرسال رابط التفعيل."
            success = True  # Always show success to prevent email enumeration
        
        if self.is_htmx(request):
            return render(request, 'accounts/partials/resend_verification_result.html', {
                'message': message,
                'success': success
            })
        
        if success:
            messages.success(request, message)
        return redirect('accounts:login')
    
    def get(self, request, *args, **kwargs):
        # Show the resend form
        if self.is_htmx(request):
            return render(request, 'accounts/partials/resend_verification_form.html')
        return render(request, 'resend_verification.html')
    
    def send_verification_email(self, user):
        from django.contrib.sites.shortcuts import get_current_site
        from django.template.loader import render_to_string
        from django.core.mail import send_mail
        
        token = email_verification_token.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        current_site = get_current_site(self.request)
        verification_url = reverse('accounts:verify_email', kwargs={
            'token': f"{uid}-{token}"
        })
        
        full_url = f"https://{current_site.domain}{verification_url}"
        
        subject = 'تفعيل حسابك - نظام المساعدات الطلابية'
        message = render_to_string('accounts/emails/verification_email.html', {
            'user': user,
            'verification_url': full_url,
        })
        
        send_mail(
            subject=subject,
            message='',
            html_message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


class CustomPasswordResetView(HTMXMixin, PasswordResetView):
    """Request password reset - HTMX enabled"""
    template_name = 'password_reset.html'
    email_template_name = 'accounts/emails/password_reset_email.html'
    success_url = reverse_lazy('accounts:password_reset_done')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_htmx'] = self.is_htmx(self.request)
        return context
    
    def form_valid(self, form):
        if self.is_htmx(self.request):
            # Process the form
            opts = {
                'use_https': self.request.is_secure(),
                'token_generator': self.token_generator,
                'from_email': self.from_email,
                'email_template_name': self.email_template_name,
                'subject_template_name': self.subject_template_name,
                'request': self.request,
                'html_email_template_name': self.html_email_template_name,
                'extra_email_context': self.extra_email_context,
            }
            form.save(**opts)
            
            return render(self.request, 'accounts/partials/password_reset_done.html', {
                'message': "تم إرسال تعليمات إعادة تعيين كلمة المرور إلى بريدك الإلكتروني."
            })
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        if self.is_htmx(self.request):
            return render(self.request, 'accounts/partials/password_reset_form.html', {
                'form': form,
                'is_htmx': True
            }, status=422)
        return super().form_invalid(form)


class CustomPasswordResetConfirmView(HTMXMixin, PasswordResetConfirmView):
    """Set new password - HTMX enabled"""
    template_name = 'password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_htmx'] = self.is_htmx(self.request)
        context['validlink'] = self.validlink
        return context
    
    def form_valid(self, form):
        if self.is_htmx(self.request):
            form.save()
            return render(self.request, 'accounts/partials/password_reset_complete.html', {
                'message': "تم إعادة تعيين كلمة المرور بنجاح. يمكنك الآن تسجيل الدخول."
            })
        return super().form_valid(form)
    
    def form_invalid(self, form):
        if self.is_htmx(self.request):
            return render(self.request, 'accounts/partials/password_reset_confirm_form.html', {
                'form': form,
                'validlink': self.validlink,
                'is_htmx': True
            }, status=422)
        return super().form_invalid(form)
    
    def get(self, request, *args, **kwargs):
        self.object = None
        # Call parent to set user and validlink
        super_result = super().get(request, *args, **kwargs)
        
        if self.is_htmx(request) and not self.validlink:
            return render(request, 'accounts/partials/password_reset_invalid.html', {
                'message': "رابط إعادة التعيين غير صالح أو منتهي الصلاحية."
            })
        
        if self.is_htmx(request):
            return render(request, 'accounts/partials/password_reset_confirm_form.html', {
                'form': self.get_form(),
                'validlink': self.validlink,
                'is_htmx': True
            })
        
        return super_result

class ChangePasswordView(LoginRequiredMixin, HTMXMixin, FormView):
    """
    View for authenticated users to change their password.
    Supports both full page load and HTMX requests.
    """
    template_name = 'accounts/change_password.html'
    form_class = PasswordChangeForm
    success_url = reverse_lazy('accounts:password_change_done')
    
    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """Save the new password and update the session."""
        user = form.save()
        update_session_auth_hash(self.request, user)
        messages.success(self.request, _('تم تغيير كلمة المرور بنجاح.'))
        
        # Check if HTMX request
        if self.request.headers.get('HX-Request'):
            # Return success message as HTML for HTMX swap
            html = render_to_string('accounts/partials/password_change_success.html', {
                'message': _('تم تغيير كلمة المرور بنجاح.')
            }, request=self.request)
            return HttpResponse(html)
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Handle form errors - return partial for HTMX."""
        if self.request.headers.get('HX-Request'):
            html = render_to_string('accounts/partials/change_password_form.html', {
                'form': form
            }, request=self.request)
            return HttpResponse(html, status=422)
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hx_target'] = 'password-change-form'
        return context
