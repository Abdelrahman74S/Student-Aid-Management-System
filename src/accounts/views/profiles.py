from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import View, DetailView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from ..models import (
    UserRoles, StudentProfile, ReviewerProfile, 
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


# -----------------------------------------------
# mahmoud 
# -----------------------------------------------

# ProfileDashboardView	
# StudentProfileDetailView	
# StudentProfileUpdateView	
# ReviewerProfileDetailView	
# ReviewerProfileUpdateView



# -----------------------------------------------
# Kareem
# -----------------------------------------------

# CommitteeHeadProfileDetailView	
# CommitteeHeadProfileUpdateView	
# AuditorProfileDetailView	
# AuditorProfileUpdateView	