from django.shortcuts import render, redirect, get_object_or_404 , reverse
from django.urls import reverse_lazy
from django.views.generic import View, DetailView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from ..models import (
    User,  StudentProfile, ReviewerProfile, 
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


# ------------------ Student ------------------
class StudentProfileDetailView(LoginRequiredMixin, StudentRequiredMixin, DetailView):
    model = StudentProfile
    template_name = 'accounts/profiles/student_detail.html'
    context_object_name = 'profile'

    def get_object(self):
        return get_object_or_404(StudentProfile, user=self.request.user)


class StudentProfileUpdateView(LoginRequiredMixin, StudentRequiredMixin, UpdateView):
    model = StudentProfile
    form_class = StudentProfileForm
    template_name = 'accounts/profiles/student_update.html'
    success_url = reverse_lazy('accounts:profile_dashboard')

    def get_object(self):
        return get_object_or_404(StudentProfile, user=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, _("تم تحديث الملف الشخصي بنجاح"))
        return super().form_valid(form)


# ------------------ Reviewer ------------------
class ReviewerProfileDetailView(LoginRequiredMixin, ReviewerRequiredMixin, DetailView):
    model = ReviewerProfile
    template_name = 'accounts/profiles/reviewer_detail.html'
    context_object_name = 'profile'

    def get_object(self):
        return get_object_or_404(ReviewerProfile, user=self.request.user)


class ReviewerProfileUpdateView(LoginRequiredMixin, ReviewerRequiredMixin, UpdateView):
    model = ReviewerProfile
    form_class = ReviewerProfileForm
    template_name = 'accounts/profiles/reviewer_update.html'
    success_url = reverse_lazy('accounts:profile_dashboard')

    def get_object(self):
        return get_object_or_404(ReviewerProfile, user=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, _("تم تحديث الملف الشخصي بنجاح"))
        return super().form_valid(form)


# ------------------ Committee Head ------------------
class CommitteeHeadProfileDetailView(LoginRequiredMixin, CommitteeHeadRequiredMixin, DetailView):
    model = CommitteeHeadProfile
    template_name = 'accounts/profiles/committee_head_detail.html'
    context_object_name = 'profile'

    def get_object(self):
        return get_object_or_404(CommitteeHeadProfile, user=self.request.user)


class CommitteeHeadProfileUpdateView(LoginRequiredMixin, CommitteeHeadRequiredMixin, UpdateView):
    model = CommitteeHeadProfile
    form_class = CommitteeHeadProfileForm
    template_name = 'accounts/profiles/committee_head_update.html'
    success_url = reverse_lazy('accounts:profile_dashboard')

    def get_object(self):
        return get_object_or_404(CommitteeHeadProfile, user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, _("تم تحديث الملف الشخصي بنجاح"))
        return super().form_valid(form)

# ------------------ Auditor ------------------
class AuditorProfileDetailView(LoginRequiredMixin, AuditorRequiredMixin, DetailView):
    model = AuditorProfile
    template_name = 'accounts/profiles/auditor_detail.html'
    context_object_name = 'profile'

    def get_object(self):
        return get_object_or_404(AuditorProfile, user=self.request.user)

class AuditorProfileUpdateView(LoginRequiredMixin, AuditorRequiredMixin, UpdateView):
    model = AuditorProfile
    form_class = AuditorProfileForm
    template_name = 'accounts/profiles/auditor_update.html'
    success_url = reverse_lazy('accounts:profile_dashboard')

    def get_object(self):
        return get_object_or_404(AuditorProfile, user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, _("تم تحديث الملف الشخصي بنجاح"))
        return super().form_valid(form)
