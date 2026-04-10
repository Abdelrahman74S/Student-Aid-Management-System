from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages
from .models import UserRoles

class RoleRequiredMixin(AccessMixin):
    allowed_roles = []
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if request.user.role not in self.allowed_roles:
            messages.error(request, "عذراً، ليس لديك الصلاحية للوصول إلى هذه الصفحة.")
            return redirect('accounts:dashboard_redirect')
        
        
            
        return super().dispatch(request, *args, **kwargs)


class StudentRequiredMixin(RoleRequiredMixin):
    allowed_roles = [UserRoles.STUDENT]

class ReviewerRequiredMixin(RoleRequiredMixin):
    allowed_roles = [UserRoles.REVIEWER]

class CommitteeHeadRequiredMixin(RoleRequiredMixin):
    allowed_roles = [UserRoles.COMMITTEE_HEAD]

class AuditorRequiredMixin(RoleRequiredMixin):
    allowed_roles = [UserRoles.AUDITOR]

class StaffRequiredMixin(RoleRequiredMixin):
    allowed_roles = [UserRoles.REVIEWER, UserRoles.COMMITTEE_HEAD, UserRoles.ADMIN]
    

class ReviewerProgramRequiredMixin(ReviewerRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code != 200: return response
        
        application = self.get_object() 
        reviewer_profile = request.user.reviewer_profile
        
        if not reviewer_profile.assigned_programs.filter(id=application.student.program_id).exists():
            messages.error(request, "ليس لديك صلاحية لمراجعة طلاب هذا القسم.")
            return redirect('accounts:dashboard_redirect')
        return response