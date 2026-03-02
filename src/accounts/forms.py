from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _
from .models import User, StudentProfile, ReviewerProfile, CommitteeHeadProfile

class StudentRegistrationForm(UserCreationForm):

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
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'UG_xxxxxx@science.tanta.edu.eg'})
    )
    password = forms.CharField(
        label=_("كلمة المرور"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('full_name', 'image')
        labels = {
            'full_name': _('الاسم الكامل المعروض'),
            'image': _('صورة الملف الشخصي'),
        }



class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ('program', 'level', 'student_id', 'phone', 'address', 'disability_status')
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'phone': forms.TextInput(attrs={'placeholder': '01xxxxxxxxx'}),
        }
        labels = {
            'program': _('القسم الأكاديمي'),
            'level': _('المستوى الدراسي الحالي'),
            'student_id': _('رقم الكارنيه / الرقم الجامعي'),
            'phone': _('رقم الموبايل للتواصل'),
            'address': _('عنوان السكن الحالي'),
            'disability_status': _('هل أنت من ذوي الاحتياجات الخاصة؟'),
        }


class ReviewerProfileForm(forms.ModelForm):

    class Meta:
        model = ReviewerProfile
        fields = ('academic_rank', 'specialization', 'office_location', 'bio')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }


class CommitteeHeadProfileForm(forms.ModelForm):

    class Meta:
        model = CommitteeHeadProfile
        fields = ('committee_name', 'signature_image')
        help_texts = {
            'signature_image': _('يجب أن يكون التوقيع واضحاً بخلفية بيضاء (PNG أو JPG).'),
        }