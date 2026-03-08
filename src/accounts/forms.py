from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _
from .models import (
    User, StudentProfile, ReviewerProfile, 
    CommitteeHeadProfile, AuditorProfile
)

class RegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'full_name', 'national_id')
        labels = {
            'email': _('البريد الإلكتروني الجامعي'),
            'full_name': _('الاسم الرباعي الكامل'),
            'national_id': _('الرقم القومي (14 رقم)'),
        }
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            return email.upper()
        return email

class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label=_("البريد الإلكتروني الجامعي"),
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 
            'placeholder': 'UG_xxxxxx@science.tanta.edu.eg'
        })
    )
    password = forms.CharField(
        label=_("كلمة المرور"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = (
            'program', 'level', 'student_id', 'gpa', 
            'phone', 'address', 'disability_status'
        )
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'placeholder': '01xxxxxxxxx', 'class': 'form-control'}),
            'gpa': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'program': forms.Select(attrs={'class': 'form-select'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'program': _('القسم الأكاديمي'),
            'level': _('المستوى الدراسي'),
            'student_id': _('الرقم الجامعي'),
            'gpa': _('المعدل التراكمي (GPA)'),
            'phone': _('رقم الموبايل'),
            'address': _('عنوان السكن الحالي'),
            'disability_status': _('هل أنت من ذوي الاحتياجات الخاصة؟'),
        }

class ReviewerProfileForm(forms.ModelForm):
    class Meta:
        model = ReviewerProfile
        fields = ('academic_rank', 'specialization', 'office_location', 'bio')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'office_location': forms.TextInput(attrs={'class': 'form-control'}),
            'specialization': forms.TextInput(attrs={'class': 'form-control'}),
            'academic_rank': forms.Select(attrs={'class': 'form-select'}),
        }

class CommitteeHeadProfileForm(forms.ModelForm):
    class Meta:
        model = CommitteeHeadProfile
        fields = ('committee_name', 'signature_image', 'is_active_head')
        widgets = {
            'committee_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'signature_image': _('يجب أن يكون التوقيع واضحاً بخلفية بيضاء للاعتماد الإلكتروني.'),
        }

class AuditorProfileForm(forms.ModelForm):
    class Meta:
        model = AuditorProfile
        fields = ('bio',)
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('full_name', 'image')
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
        }