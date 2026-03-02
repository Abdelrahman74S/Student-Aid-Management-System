from django.views.generic import ListView, UpdateView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, FileResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from .auth_views import HTMXMixin
from ..models import UserRoles, CommitteeHeadProfile, StudentProfile, Program


class CommitteeHeadRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return (
            self.request.user.role == UserRoles.COMMITTEE_HEAD and 
            self.request.user.is_staff
        )
    
    def handle_no_permission(self):
        if self.request.headers.get('HX-Request'):
            return HttpResponse(
                '<div class="alert alert-error">يتطلب صلاحيات رئيس لجنة</div>',
                status=403
            )
        return super().handle_no_permission()


class CommitteeDashboardView(LoginRequiredMixin, CommitteeHeadRequiredMixin, HTMXMixin, View):
    template_name = 'committee/dashboard.html'
    partial_template_name = 'committee/partials/stats_cards.html'
    
    def get(self, request, *args, **kwargs):
        profile = get_object_or_404(CommitteeHeadProfile, user=request.user)
        
        managed_programs = profile.managed_programs.all()
        
        stats = {
            'total_students': StudentProfile.objects.filter(
                program__in=managed_programs
            ).count(),
            'pending_approvals': 0,  
            'committee_name': profile.committee_name,
            'authority_level': profile.authority_level,
        }
        
        return render(request, self.get_template_names()[0], {
            'profile': profile,
            'stats': stats,
            'managed_programs': managed_programs
        })


class CommitteeProfileUpdateView(LoginRequiredMixin, CommitteeHeadRequiredMixin, HTMXMixin, UpdateView):

    model = CommitteeHeadProfile
    fields = ['committee_name', 'signature_image', 'managed_programs']
    template_name = 'committee/profile_edit.html'
    partial_template_name = 'committee/partials/profile_form.html'
    success_url = reverse_lazy('committee_dashboard')
    
    def get_object(self):
        return get_object_or_404(CommitteeHeadProfile, user=self.request.user)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        if self.is_htmx_request():
            # معاينة التوقيع المحدث
            if self.object.signature_image:
                return HttpResponse(
                    f'''
                    <div class="alert alert-success">تم حفظ التوقيع</div>
                    <img src="{self.object.signature_image.url}" class="signature-preview mt-4 border rounded" style="max-height: 100px;">
                    ''',
                    headers={'HX-Trigger': 'signatureUpdated'}
                )
            return HttpResponse(
                '<div class="alert alert-success">تم الحفظ</div>',
                headers={'HX-Trigger': 'profileUpdated'}
            )
        return response


class DocumentSignView(LoginRequiredMixin, CommitteeHeadRequiredMixin, View):
    def get(self, request, document_id, *args, **kwargs):
        profile = get_object_or_404(CommitteeHeadProfile, user=request.user)
        
        if not profile.signature_image:
            return HttpResponse(
                '''
                <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                    <p class="text-yellow-700">يجب رفع توقيعك أولاً من <a href="/committee/profile/" class="underline">الإعدادات</a></p>
                </div>
                ''',
                status=400
            )
        
        return render(request, 'committee/partials/sign_modal.html', {
            'document_id': document_id,
            'signature_url': profile.signature_image.url
        })
    
    def post(self, request, document_id, *args, **kwargs):
        profile = get_object_or_404(CommitteeHeadProfile, user=request.user)

        return HttpResponse(
            '''
            <div class="bg-green-50 border border-green-200 rounded-lg p-4">
                <div class="flex items-center">
                    <svg class="w-6 h-6 text-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <span class="text-green-800 font-medium">تم توقيع المستند بنجاح</span>
                </div>
            </div>
            ''',
            headers={
                'HX-Trigger': 'documentSigned',
                'HX-Retarget': '#sign-modal'
            }
        )


class CommitteeMembersView(LoginRequiredMixin, CommitteeHeadRequiredMixin, HTMXMixin, ListView):

    template_name = 'committee/members.html'
    partial_template_name = 'committee/partials/members_list.html'
    context_object_name = 'members'
    
    def get_queryset(self):
        return []