import uuid
import os
from django.db import models
from django.conf import settings
from aid_management.models import AidApplication, SupportCycle 
import hashlib
import hmac

# دالة لتنظيم تخزين الملفات بشكل شجري (سنة/شهر/طالب)
def get_file_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join(f'documents/{instance.application.student.id}/', filename)

# ==============================
# 1. موديل مستندات الطالب (ApplicationDocument)
# ==============================
class ApplicationDocument(models.Model):
    """
    هذا الموديل يمثل 'المدخلات'. بدلاً من كتابة البيانات ورقياً، يرفع الطالب 
    إثباتاته (البطاقة، مفردات المرتب) لكي تظهر للموظف إلكترونياً.
    """
    DOCUMENT_TYPES = [
        ('NATIONAL_ID', 'صورة الرقم القومي'),
        ('INCOME_PROOF', 'إثبات الدخل / مفردات مرتب'),
        ('SOCIAL_RESEARCH', 'البحث الاجتماعي الخارجي'),
        ('MEDICAL_DOC', 'تقرير طبي'),
        ('OTHER', 'مستندات إضافية'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        AidApplication, 
        on_delete=models.CASCADE, 
        related_name='documents',
        verbose_name="الطلب المرتبط"
    ) 
    
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, verbose_name="نوع المستند")
    file = models.FileField(upload_to=get_file_path, verbose_name="الملف المرفق")
    
    # حقول الحوكمة والتحقق الإداري
    is_verified = models.BooleanField(default=False, verbose_name="تم التحقق من صحته")
    verification_note = models.TextField(blank=True, verbose_name="ملاحظات المراجع")
    
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مستند مرفق"
        verbose_name_plural = "مستندات الطلبات"

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.application.serial_number}"


# ==============================
# 2. موديل الأرشفة والتقارير الرسمية (OfficialReport)
# ==============================
class OfficialReport(models.Model):
    """
    هذا الموديل يمثل 'المخرجات'. هو المحرك الذي يجمع بيانات الطالب وقرار اللجنة 
    ويحولها إلى ملف PDF جاهز للطباعة والختم كما طلب الدكتور.
    """
    report_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    application = models.OneToOneField(
        AidApplication, 
        on_delete=models.CASCADE, 
        related_name='official_report'
    ) 
    
    # نسخة رقمية مخزنة للتقرير وقت صدوره (SnapShot) لضمان عدم التلاعب
    pdf_version = models.FileField(upload_to='reports/archives/%Y/', null=True, blank=True)
    
    # بيانات رقمية مضافة للطباعة (QR Code للتحقق من الصحة)
    verification_qr = models.ImageField(upload_to='reports/qr/', null=True, blank=True)
    
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = "تقرير رسمي"
        verbose_name_plural = "أرشيف التقارير الرسمية"

class SocialResearchForm(models.Model):
    """النسخة الرقمية من استمارة البحث الاجتماعي (التي يملأها الباحث)"""
    HOUSING_TYPES = [('OWN', 'تمليك'), ('RENT', 'إيجار'), ('OLD_RENT', 'إيجار قديم')]
    
    application = models.OneToOneField('aid_management.AidApplication', on_delete=models.CASCADE, related_name='social_research')
    
    # تفاصيل السكن (موجودة في الورقة الرسمية)
    housing_type = models.CharField(max_length=20, choices=HOUSING_TYPES, verbose_name="نوع السكن")
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="القيمة الإيجارية")
    
    
    # رأي الباحث الاجتماعي (الذي يُطبع في أسفل الورقة)
    researcher_opinion = models.TextField(verbose_name="رأي الباحث الاجتماعي وتوصيته")
    researcher_name = models.CharField(max_length=255)
    
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "استمارة بحث اجتماعي"
        verbose_name_plural = "استمارات البحوث الاجتماعية"

class CommitteeMeetingMinute(models.Model):
    """يمثل 'محضر اجتماع اللجنة' الرسمي الذي يوقع عليه الأعضاء"""
    meeting_date = models.DateField(verbose_name="تاريخ انعقاد اللجنة")
    meeting_number = models.PositiveIntegerField(verbose_name="رقم الاجتماع")
    
    # رئيس اللجنة والأعضاء الحاضرون
    head_of_committee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    attendees = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='attended_meetings')
    
    
    # تجميع الطلبات التي تمت الموافقة عليها في هذا الاجتماع
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

    # ← الإضافة الأساسية: ربط بالتخصيص الرسمي
    allocation = models.OneToOneField(
        'aid_management.BudgetAllocation',
        on_delete=models.PROTECT,          # لا تحذف التخصيص لو في قسيمة مرتبطة
        null=True,
        blank=True,
        related_name='voucher',
        verbose_name="التخصيص المرتبط"
    )

    # amount الآن read-only من الـ allocation — لكن نحتفظ بحقل للطباعة
    amount      = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date = models.DateField()

    verification_hash = models.CharField(max_length=100, unique=True)
    is_printed        = models.BooleanField(default=False)
    printed_at        = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name        = "قسيمة صرف"
        verbose_name_plural = "قسائم الصرف"

    def _generate_hash(self):
        """HMAC-SHA256 يضمن إن القسيمة طلعت من النظام"""
        secret  = settings.SECRET_KEY.encode()
        message = f"{self.voucher_number}:{self.amount}:{self.application_id}".encode()
        return hmac.new(secret, message, hashlib.sha256).hexdigest()

    def clean(self):
        from django.core.exceptions import ValidationError
        # التأكد إن مبلغ القسيمة = مبلغ التخصيص المعتمد
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
        # مزامنة المبلغ من الـ allocation تلقائياً
        if self.allocation_id and not kwargs.get('update_fields'):
            self.amount = self.allocation.amount_allocated

        # توليد الـ hash لو جديد أو تغير الـ voucher_number
        if not self.verification_hash:
            self.verification_hash = self._generate_hash()

        self.full_clean()
        super().save(*args, **kwargs)

    def verify(self, hash_to_check: str) -> bool:
        """يُستخدم في الـ QR endpoint للتحقق من صحة القسيمة"""
        return hmac.compare_digest(self.verification_hash, hash_to_check)