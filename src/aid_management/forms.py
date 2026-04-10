from django import forms
from django.utils.translation import gettext_lazy as _
from jsonschema import ValidationError
from .models import AidApplication, SupportCycle, ScoringRule, CommitteeReview
import json


# ==============================
# 1. نموذج تقديم الطالب
# ==============================
class StudentApplicationForm(forms.ModelForm):
    father_income = forms.DecimalField(
        label=_("دخل الأب الشهري"),
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00'
        })
    )
    mother_income = forms.DecimalField(
        label=_("دخل الأم الشهري"),
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00'
        })
    )
    family_members = forms.IntegerField(
        label=_("عدد أفراد الأسرة"),
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    housing_status = forms.ChoiceField(
        label=_("حالة السكن"),
        choices=[('RENT', _('إيجار')), ('OWN', _('تمليك'))],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = AidApplication
        fields = ['student', 'cycle']
        widgets = {
            'student': forms.HiddenInput(),
            'cycle': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data = {}
        if self.instance and self.instance.pk and self.instance.financial_assessment:
            data = self.instance.financial_assessment

        if data:
            self.fields['father_income'].initial = data.get('father_income')
            self.fields['mother_income'].initial = data.get('mother_income')
            self.fields['family_members'].initial = data.get('family_members')
            self.fields['housing_status'].initial = data.get('housing_status')

    def save(self, commit=True):
        instance = super().save(commit=False)

        instance.financial_assessment = {
            'father_income': str(self.cleaned_data['father_income']),
            'mother_income': str(self.cleaned_data['mother_income']),
            'family_members': self.cleaned_data['family_members'],
            'housing_status': self.cleaned_data['housing_status'],
        }

        if commit:
            instance.save()
        return instance
    

# ==============================
# 2. نموذج مراجعة اللجنة
# ==============================
class CommitteeReviewForm(forms.ModelForm):
    class Meta:
        model = CommitteeReview
        fields = ['conflict_of_interest', 'qualitative_notes']
        widgets = {
            'conflict_of_interest': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'qualitative_notes': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.application = kwargs.pop('application', None)
        super().__init__(*args, **kwargs)

        if self.application:
            rules = ScoringRule.objects.filter(
                cycle=self.application.cycle,
                is_active=True
            ).select_related('cycle')

            for rule in rules:
                field_name = f"score_{rule.criteria_type.lower()}"
                self.fields[field_name] = forms.IntegerField(
                    label=rule.get_criteria_type_display(),
                    min_value=0,
                    max_value=rule.points,
                    required=True,
                    widget=forms.NumberInput(attrs={'class': 'form-control'}),
                    help_text=_("الحد الأقصى للنقاط: %(pts)s") % {
                        'pts': rule.points
                    }
                )
            
            if self.instance and self.instance.pk and self.instance.dimension_scores:
                for key, value in self.instance.dimension_scores.items():
                    field_name = f"score_{key.lower()}"
                    if field_name in self.fields:
                        self.fields[field_name].initial = value

    def save(self, commit=True):
        instance = super().save(commit=False)

        dimension_scores = {}
        for field_name, value in self.cleaned_data.items():
            if field_name.startswith('score_'):
                dimension_key = field_name[len('score_'):]
                dimension_scores[dimension_key] = value

        instance.dimension_scores = dimension_scores

        if commit:
            instance.save()
        return instance

