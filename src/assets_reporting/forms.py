from django import forms
from .models import ApplicationDocument, SocialResearchForm, CommitteeMeetingMinute, DisbursementVoucher
from django.utils.translation import gettext_lazy as _

class TailwindFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            existing_classes = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f"{existing_classes} w-full bg-gray-50 border border-gray-200 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block p-3 transition-all"

class ApplicationDocumentForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = ApplicationDocument
        fields = ['document_type', 'file']
        labels = {
            'document_type': _('نوع المستند المرفق'),
            'file': _('اختر الملف (PDF أو صورة)'),
        }
        help_texts = {
            'file': _('يرجى التأكد من وضوح المستند قبل الرفع.'),
        }

class DigitalSocialResearchForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = SocialResearchForm
        fields = ['housing_type', 'monthly_rent', 'researcher_name', 'researcher_opinion']
        labels = {
            'housing_type': _('نوع السكن الحالي'),
            'monthly_rent': _('قيمة الإيجار الشهري (إن وجد)'),
            'researcher_name': _('اسم الباحث الاجتماعي القائم بالبحث'),
            'researcher_opinion': _('التوصية الفنية والبحثية'),
        }
        widgets = {
            'researcher_opinion': forms.Textarea(attrs={'rows': 4, 'placeholder': 'اكتب تفاصيل الحالة ورأيك الفني هنا...'}),
        }

class CommitteeMeetingForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = CommitteeMeetingMinute
        fields = ['meeting_date', 'meeting_number', 'head_of_committee', 'attendees', 'approved_applications']
        labels = {
            'meeting_date': _('تاريخ انعقاد الاجتماع'),
            'meeting_number': _('رقم محضر الاجتماع'),
            'head_of_committee': _('رئيس اللجنة'),
            'attendees': _('الأعضاء الحاضرون'),
            'approved_applications': _('الطلاب الذين تمت الموافقة عليهم'),
        }
        widgets = {
            'meeting_date': forms.DateInput(attrs={'type': 'date'}),
            # استخدام CheckboxSelectMultiple لجعل اختيار الطلاب أسهل في الميكنة
            'approved_applications': forms.CheckboxSelectMultiple(attrs={'class': 'grid grid-cols-1 md:grid-cols-2 gap-2'}),
            'attendees': forms.CheckboxSelectMultiple(),
        }

class DisbursementVoucherForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = DisbursementVoucher
        fields = ['status', 'voucher_number', 'expiry_date']
        labels = {
            'status': _('حالة القسيمة'),
            'voucher_number': _('رقم القسيمة الدفتري'),
            'expiry_date': _('تاريخ انتهاء صلاحية الصرف'),
        }
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }