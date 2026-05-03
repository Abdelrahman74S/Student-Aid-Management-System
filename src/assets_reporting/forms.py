# documents/forms.py
import os
from datetime import date
from django import forms
from .models import (
    ApplicationDocument,
    SocialResearchForm as SocialResearchModel,
    CommitteeMeetingMinute,
    DisbursementVoucher,
)


class ApplicationDocumentForm(forms.ModelForm):
    class Meta:
        model = ApplicationDocument
        fields = ['document_type', 'file']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png',
            }),
        }
        labels = {
            'document_type': 'نوع المستند',
            'file':          'الملف المرفق',
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError('حجم الملف يتجاوز 5MB')
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
                raise forms.ValidationError('نوع الملف غير مسموح')
        return file


ApplicationDocumentFormSet = forms.modelformset_factory(
    ApplicationDocument,
    form=ApplicationDocumentForm,
    extra=3,
    can_delete=True,
)


class SocialResearchDataForm(forms.ModelForm):

    class Meta:
        model = SocialResearchModel
        fields = ['housing_type','monthly_rent','researcher_opinion','researcher_name']
        widgets = {
            'housing_type':       forms.RadioSelect(),
            'monthly_rent':       forms.NumberInput(attrs={'class':'form-control','min':0}),
            'researcher_opinion': forms.Textarea(attrs={'class':'form-control','rows':4}),
            'researcher_name':    forms.TextInput(attrs={'class':'form-control'}),
        }


    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.has_appliances = {
            'ثلاجة':    self.cleaned_data.get('has_fridge', False),
            'تكييف':    self.cleaned_data.get('has_ac', False),
            'غسالة':    self.cleaned_data.get('has_washer', False),
            'تليفزيون': self.cleaned_data.get('has_tv', False),
            'سيارة':    self.cleaned_data.get('has_car', False),
        }
        if commit:
            instance.save()
        return instance


class CommitteeMeetingMinuteForm(forms.ModelForm):
    class Meta:
        model = CommitteeMeetingMinute
        fields = ['meeting_date','meeting_number','head_of_committee',
            'attendees','approved_applications','official_document']
        widgets = {
            'meeting_date':          forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'meeting_number':        forms.NumberInput(attrs={'class':'form-control','min':1}),
            'head_of_committee':     forms.Select(attrs={'class':'form-select'}),
            'attendees':             forms.CheckboxSelectMultiple(),
            'approved_applications': forms.CheckboxSelectMultiple(),
            'official_document':     forms.ClearableFileInput(attrs={'class':'form-control','accept':'.pdf'}),
        }

    def clean(self):
        cleaned   = super().clean()
        head      = cleaned.get('head_of_committee')
        attendees = cleaned.get('attendees')
        if head and attendees and head not in attendees:
            self.add_error('attendees','رئيس اللجنة يجب أن يكون ضمن الحاضرين')
        return cleaned


class DisbursementVoucherForm(forms.ModelForm):
    class Meta:
        model = DisbursementVoucher
        fields = ['voucher_number','amount','expiry_date','status']
        widgets = {
            'voucher_number': forms.TextInput(attrs={'class':'form-control'}),
            'amount':         forms.NumberInput(attrs={'class':'form-control','min':0,'step':'0.01'}),
            'expiry_date':    forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'status':         forms.Select(attrs={'class':'form-select'}),
        }

    def clean_expiry_date(self):
        expiry = self.cleaned_data.get('expiry_date')
        if expiry and expiry < date.today():
            raise forms.ValidationError('التاريخ لا يمكن أن يكون في الماضي')
        return expiry

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('المبلغ يجب أن يكون أكبر من صفر')
        return amount