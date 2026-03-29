import uuid
from django.shortcuts import render, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import View, CreateView, FormView
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.http import HttpResponse
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.utils.translation import gettext_lazy as _
from ..models import User, StudentProfile
from ..forms import RegistrationForm, UserLoginForm
from ..tokens import email_verification_token

class RegisterView(CreateView):
    model = User
    form_class = RegistrationForm
    template_name = 'register.html'
    success_url = reverse_lazy('accounts:login')

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(reverse('accounts:dashboard'))
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save(commit=False)
        user.role = User.Role.STUDENT
        user.is_active = True  
        user.is_verified = False
        user.save()

        StudentProfile.objects.create(user=user)

        self.send_verification_email(user)

        success_message = (
            "تم إنشاء الحساب بنجاح! "
            "يرجى التحقق من بريدك الإلكتروني لتفعيل الحساب."
        )

        messages.success(self.request, success_message)
        return redirect(self.success_url)

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


class UserLoginView(FormView):
    template_name = 'login.html'
    form_class = UserLoginForm

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(reverse('accounts:dashboard'))
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        email = form.cleaned_data.get('username') 
        password = form.cleaned_data.get('password')

        user = authenticate(self.request, username=email, password=password)

        if user is not None:
            if not user.is_active:
                error_msg = "الحساب معطل. يرجى التواصل مع الإدارة."
                messages.error(self.request, error_msg)
                return self.render_to_response(self.get_context_data(form=form))

            login(self.request, user)

            next_url = self.request.POST.get('next') or self.request.GET.get('next')
            if next_url:
                return redirect(next_url)
            else:
                return redirect('accounts:dashboard')

        error_msg = "البريد الإلكتروني أو كلمة المرور غير صحيحة."
        messages.error(self.request, error_msg)
        return self.render_to_response(self.get_context_data(form=form))


class UserLogoutView(LoginRequiredMixin,View):
    def post(self, request, *args, **kwargs):
        logout(request)
        messages.success(request, "تم تسجيل الخروج بنجاح.")
        return redirect('accounts:login')

    def get(self, request, *args, **kwargs):
        return redirect('accounts:login')


class EmailVerificationView(View):
    template_name = 'verification_result.html'

    def get(self, request, token, *args, **kwargs):
        try:
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

        return render(request, self.template_name, context)


class ResendVerificationEmailView(View):
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email', '').strip().upper()

        try:
            user = User.objects.get(email=email, is_verified=False)
            self.send_verification_email(user)
            message = "تم إرسال رابط التفعيل الجديد إلى بريدك الإلكتروني."
            success = True
        except User.DoesNotExist:
            message = "إذا كان البريد الإلكتروني مسجلاً وغير مفعل، فسيتم إرسال رابط التفعيل."
            success = True  

        messages.success(request, message)
        return redirect('accounts:login')

    def get(self, request, *args, **kwargs):
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


class CustomPasswordResetView(PasswordResetView):
    template_name = 'password_reset.html'
    email_template_name = 'accounts/emails/password_reset_email.html'
    success_url = reverse_lazy('accounts:password_reset_done')


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class ChangePasswordView(LoginRequiredMixin, FormView):
    template_name = 'accounts/change_password.html'
    form_class = PasswordChangeForm
    success_url = reverse_lazy('accounts:password_change_done')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        update_session_auth_hash(self.request, user)
        messages.success(self.request, _('تم تغيير كلمة المرور بنجاح.'))
        return super().form_valid(form)