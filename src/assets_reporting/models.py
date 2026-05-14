import uuid
import os
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from aid_management.models import AidApplication, SupportCycle 
import hashlib
import hmac
import qrcode
from io import BytesIO
from django.core.files import File


def get_file_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join(f'documents/{instance.application.student.id}/', filename)

# ==============================

class DocumentType(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name=_("كود النوع"))
    name = models.CharField(max_length=255, verbose_name=_("اسم المستند"))

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _("نوع مستند")
        verbose_name_plural = _("أنواع المستندات")

# ==============================
class ApplicationDocument(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        AidApplication, 
        on_delete=models.CASCADE, 
        related_name='documents',
        verbose_name="الطلب المرتبط"
    ) 
    
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE, verbose_name="نوع المستند")
    file = models.FileField(upload_to=get_file_path, verbose_name="الملف المرفق")
    
    # حقول الحوكمة والتحقق الإداري
    is_verified = models.BooleanField(default=False, verbose_name="تم التحقق من صحته")
    verification_note = models.TextField(blank=True, verbose_name="ملاحظات المراجع")
    
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مستند مرفق"
        verbose_name_plural = "مستندات الطلبات"

    def __str__(self):
        return f"{self.document_type.name} - {self.application.serial_number}"


# ==============================
# 2. موديل الأرشفة والتقارير الرسمية (OfficialReport)
# ==============================
class OfficialReport(models.Model):

    report_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    application = models.OneToOneField(
        AidApplication, 
        on_delete=models.CASCADE, 
        related_name='official_report'
    ) 
    
    pdf_version = models.FileField(upload_to='reports/archives/%Y/', null=True, blank=True)
    
    verification_qr = models.ImageField(upload_to='reports/qr/', null=True, blank=True)
    
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = "تقرير رسمي"
        verbose_name_plural = "أرشيف التقارير الرسمية"

class SocialResearchForm(models.Model):
    HOUSING_TYPES = [
        ('OWN', _('تمليك')), 
        ('RENT', _('إيجار')), 
        ('OLD_RENT', _('إيجار قديم'))
    ]
    
    application = models.OneToOneField('aid_management.AidApplication', on_delete=models.CASCADE, related_name='social_research')
    
    housing_type = models.CharField(max_length=20, choices=HOUSING_TYPES, verbose_name="نوع السكن")
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="القيمة الإيجارية")
    
    
    researcher_opinion = models.TextField(verbose_name=_("رأي الباحث الاجتماعي وتوصيته"))
    researcher_name = models.CharField(max_length=255, verbose_name=_("اسم الباحث"))
    
    research_document = models.FileField(upload_to='research_documents/%Y/', null=True, blank=True, verbose_name="ملف البحث الميداني (Word/PDF)")
    
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "استمارة بحث اجتماعي"
        verbose_name_plural = "استمارات البحوث الاجتماعية"

class CommitteeMeetingMinute(models.Model):
    meeting_date = models.DateField(verbose_name="تاريخ انعقاد اللجنة")
    meeting_number = models.PositiveIntegerField(verbose_name="رقم الاجتماع")
    
    head_of_committee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    attendees = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='attended_meetings')
    
    
    approved_applications = models.ManyToManyField('aid_management.AidApplication', verbose_name="الطلبات المعتمدة")
    
    official_document = models.FileField(upload_to='minutes/%Y/', null=True, blank=True, verbose_name="النسخة الموقعة والممسوحة ضوئياً")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "محضر اجتماع لجنة"
        verbose_name_plural = "محاضر اجتماعات اللجان"


class DisbursementVoucher(models.Model):
    VOUCHER_STATUS = [
        ('PENDING', 'بانتظار الصرف'),
        ('PAID',    'تم الصرف'),
        ('EXPIRED', 'منتهي الصلاحية'),
    ]

    status         = models.CharField(max_length=10, choices=VOUCHER_STATUS, default='PENDING')
    voucher_number = models.CharField(max_length=50, unique=True)
    application    = models.OneToOneField(
        'aid_management.AidApplication',
        on_delete=models.CASCADE
    )

    allocation = models.OneToOneField(
        'aid_management.BudgetAllocation',
        on_delete=models.PROTECT,        
        null=True,
        blank=True,
        related_name='voucher',
        verbose_name="التخصيص المرتبط"
    )

    amount      = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date = models.DateField()

    verification_hash = models.CharField(max_length=100, unique=True)
    qr_code = models.ImageField(upload_to='vouchers/qr/', blank=True, null=True, verbose_name="رمز QR")
    is_printed        = models.BooleanField(default=False)
    printed_at        = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name        = "قسيمة صرف"
        verbose_name_plural = "قسائم الصرف"

    def _generate_hash(self):
        secret  = settings.SECRET_KEY.encode()
        message = f"{self.voucher_number}:{self.amount:.2f}:{self.application_id}".encode()
        return hmac.new(secret, message, hashlib.sha256).hexdigest()

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.allocation and self.amount:
            if self.amount != self.allocation.amount_allocated:
                raise ValidationError({
                    'amount': (
                        f"مبلغ القسيمة ({self.amount}) "
                        f"يجب أن يساوي المبلغ المعتمد "
                        f"({self.allocation.amount_allocated})"
                    )
                })

    def save(self, *args, **kwargs):
        if self.allocation_id and not kwargs.get('update_fields'):
            self.amount = self.allocation.amount_allocated

        if not self.verification_hash:
            self.verification_hash = self._generate_hash()

        if not self.qr_code:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(f"Voucher: {self.voucher_number}\nHash: {self.verification_hash}")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            file_name = f"qr_{self.voucher_number}.png"
            self.qr_code.save(file_name, File(buffer), save=False)

        self.full_clean()
        super().save(*args, **kwargs)

    def verify(self, hash_to_check: str) -> bool:
        return hmac.compare_digest(self.verification_hash, hash_to_check)

class SystemTemplate(models.Model):
    ROLE_CHOICES = [
        ('S', 'طالب'),
        ('R', 'مُراجع (باحث اجتماعي)'),
        ('C', 'رئيس/عضو لجنة'),
        ('A', 'مدير النظام'),
        ('D', 'مراقب/مدقق'),
    ]
    name = models.CharField(max_length=255, verbose_name="اسم النموذج")
    file = models.FileField(upload_to='system_templates/', verbose_name="ملف النموذج")
    role_required = models.CharField(max_length=1, choices=ROLE_CHOICES, verbose_name="الدور المخصص له")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "نموذج نظام"
        verbose_name_plural = "نماذج النظام المخصصة"

    def __str__(self):
        return f"{self.name} - ({self.get_role_required_display()})"