from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.urls import reverse_lazy
from django.views.generic import View, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from ..models import (
    User, StudentProfile, ReviewerProfile, 
    CommitteeHeadProfile, AuditorProfile
)
from ..forms import (
    UserUpdateForm, StudentProfileForm, ReviewerProfileForm, 
    CommitteeHeadProfileForm, AuditorProfileForm
)
from ..mixins import (
    StudentRequiredMixin, ReviewerRequiredMixin, 
    CommitteeHeadRequiredMixin, AuditorRequiredMixin
)

class ProfileDashboardView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user = request.user
        role_redirect_map = {
            User.Role.STUDENT: 'accounts:student_profile_detail',
            User.Role.REVIEWER: 'accounts:reviewer_profile_detail',
            User.Role.COMMITTEE_HEAD: 'accounts:committee_head_profile_detail',
            User.Role.AUDITOR: 'accounts:auditor_profile_detail',
        }
        redirect_url = role_redirect_map.get(user.role)
        if redirect_url:
            return redirect(reverse(redirect_url))
        return redirect(reverse('accounts:login'))


# ------------------ Student (طالب) ------------------
class StudentProfileDetailView(LoginRequiredMixin, StudentRequiredMixin, DetailView):
    model = StudentProfile
    template_name = 'accounts/profiles/student_detail.html'
    context_object_name = 'profile'

    def get_object(self):
        return get_object_or_404(StudentProfile, user=self.request.user)

class StudentProfileUpdateView(LoginRequiredMixin, StudentRequiredMixin, View):
    template_name = 'accounts/profiles/student_update.html'

    def get(self, request, *args, **kwargs):
        profile = get_object_or_404(StudentProfile, user=request.user)
        user_form = UserUpdateForm(instance=request.user)
        profile_form = StudentProfileForm(instance=profile)
        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form
        })

    def post(self, request, *args, **kwargs):
        profile = get_object_or_404(StudentProfile, user=request.user)
        user_form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        profile_form = StudentProfileForm(request.POST, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, _("تم تحديث البيانات الشخصية والدراسية بنجاح"))
            return redirect('accounts:dashboard')
        
        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form
        })


# ------------------ Reviewer (مُراجع) ------------------
class ReviewerProfileDetailView(LoginRequiredMixin, ReviewerRequiredMixin, DetailView):
    model = ReviewerProfile
    template_name = 'accounts/profiles/reviewer_detail.html'
    context_object_name = 'profile'

    def get_object(self):
        return get_object_or_404(ReviewerProfile, user=self.request.user)

class ReviewerProfileUpdateView(LoginRequiredMixin, ReviewerRequiredMixin, View):
    template_name = 'accounts/profiles/reviewer_update.html'

    def get(self, request, *args, **kwargs):
        profile = get_object_or_404(ReviewerProfile, user=request.user)
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ReviewerProfileForm(instance=profile)
        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form
        })

    def post(self, request, *args, **kwargs):
        profile = get_object_or_404(ReviewerProfile, user=request.user)
        user_form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        profile_form = ReviewerProfileForm(request.POST, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, _("تم تحديث البيانات الشخصية والمهنية بنجاح"))
            return redirect('accounts:dashboard')
        
        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form
        })


# ------------------ Committee Head (رئيس لجنة) ------------------
class CommitteeHeadProfileDetailView(LoginRequiredMixin, CommitteeHeadRequiredMixin, DetailView):
    model = CommitteeHeadProfile
    template_name = 'accounts/profiles/committee_head_detail.html'
    context_object_name = 'profile'

    def get_object(self):
        return get_object_or_404(CommitteeHeadProfile, user=self.request.user)

class CommitteeHeadProfileUpdateView(LoginRequiredMixin, CommitteeHeadRequiredMixin, View):
    template_name = 'accounts/profiles/committee_head_update.html'

    def get(self, request, *args, **kwargs):
        profile = get_object_or_404(CommitteeHeadProfile, user=request.user)
        user_form = UserUpdateForm(instance=request.user)
        profile_form = CommitteeHeadProfileForm(instance=profile)
        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form
        })
    
    def post(self, request, *args, **kwargs):
        profile = get_object_or_404(CommitteeHeadProfile, user=request.user)
        user_form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        profile_form = CommitteeHeadProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, _("تم تحديث بيانات رئيس اللجنة بنجاح"))
            return redirect('accounts:dashboard')
        
        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form
        })


# ------------------ Auditor (المراقب) ------------------
class AuditorProfileDetailView(LoginRequiredMixin, AuditorRequiredMixin, DetailView):
    model = AuditorProfile
    template_name = 'accounts/profiles/auditor_detail.html'
    context_object_name = 'profile'
    
    def get_object(self):
        return get_object_or_404(AuditorProfile, user=self.request.user)

class AuditorProfileUpdateView(LoginRequiredMixin, AuditorRequiredMixin, View):
    template_name = 'accounts/profiles/auditor_update.html'

    def get(self, request, *args, **kwargs):
        profile = get_object_or_404(AuditorProfile, user=request.user)
        user_form = UserUpdateForm(instance=request.user)
        profile_form = AuditorProfileForm(instance=profile)
        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form
        })

    def post(self, request, *args, **kwargs):
        profile = get_object_or_404(AuditorProfile, user=request.user)
        user_form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        profile_form = AuditorProfileForm(request.POST, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, _("تم تحديث بيانات المراقب بنجاح"))
            return redirect('accounts:dashboard')
        
        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form
        })