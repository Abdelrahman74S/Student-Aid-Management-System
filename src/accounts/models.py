from django.db import models

# Create your models here.
import uuid
from typing import Optional
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class UserRoles:
    STUDENT = 'S'
    REVIEWER = 'R'
    COMMITTEE_HEAD = 'C'
    ADMIN = 'A'
    AUDITOR = 'D'


# --- Validators ---
tanta_email_validator = RegexValidator(
    regex=r'(?i)^UG_\d+@science\.tanta\.edu\.eg$', 
    message=_("يجب استخدام البريد الجامعي الرسمي لجامعة طنطا (علوم)، مثال: UG_5945090@science.tanta.edu.eg"),
    code='invalid_university_email'
)

egyptian_phone_validator = RegexValidator(
    regex=r'^01[0125]\d{8}$',
    message=_("رقم الهاتف يجب أن يكون رقم موبايل مصري صحيح (11 رقم) يبدأ بـ 010، 011، 012، أو 015."),
    code='invalid_egyptian_phone'
)

national_id_validator = RegexValidator(
    regex=r'^\d{14}$', 
    message=_("الرقم القومي يجب أن يتكون من 14 رقماً بالضبط.")
)

def validate_signature_image(image):
    if image.size > 5 * 1024 * 1024: 
        raise ValidationError(_("حجم الصورة يجب أن لا يتجاوز 5 ميجابايت"))
    if not image.name.lower().endswith(('.png', '.jpg', '.jpeg')):
        raise ValidationError(_("يُسمح فقط بملفات PNG و JPG"))


# --- Mixins ---
class RoleValidatedProfileMixin(models.Model):
    required_role: Optional[str] = None
    
    class Meta:
        abstract = True
    
    def clean(self):
        super().clean()
        if self.required_role and self.user.role != self.required_role:
            raise ValidationError(
                _("هذا الملف يجب أن ينتمي لمستخدم من نوع '{}' فقط.").format(self.required_role)
            )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# --- User Manager ---
class UserQuerySet(models.QuerySet):
    def students(self):
        return self.filter(role=UserRoles.STUDENT)

    def reviewers(self):
        return self.filter(role=UserRoles.REVIEWER)

    def committee_heads(self):
        return self.filter(role=UserRoles.COMMITTEE_HEAD)
    
    def auditors(self):
        return self.filter(role=UserRoles.AUDITOR)

    def admins(self):
        return self.filter(role=UserRoles.ADMIN)


class UserManager(BaseUserManager):
    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('يجب تزويد البريد الإلكتروني'))
        
        email = self.normalize_email(email).lower()
        local, domain = email.split('@')
        
        normalized_email = f"{local.upper()}@{domain.lower()}"
        extra_fields['username'] = local.upper()
        
        user = self.model(email=normalized_email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRoles.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('يجب أن يكون المشرف العام possesses is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('يجب أن يكون المشرف العام possesses is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


# --- User Model ---
class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = UserRoles.STUDENT, _('طالب')
        REVIEWER = UserRoles.REVIEWER, _('مُراجع')
        COMMITTEE_HEAD = UserRoles.COMMITTEE_HEAD, _('رئيس لجنة')
        AUDITOR = UserRoles.AUDITOR, _('المراقب')
        ADMIN = UserRoles.ADMIN, _('مدير نظام')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    email = models.EmailField(
        _('البريد الإلكتروني الجامعي'), 
        unique=True, 
        db_index=True,
        validators=[tanta_email_validator], 
        help_text=_("مثال: UG_5985405@science.tanta.edu.eg")
    )
    
    full_name = models.CharField(_('الاسم الكامل'), max_length=255)
    
    national_id = models.CharField(
        _('الرقم القومي'),
        max_length=14, 
        unique=True, 
        validators=[national_id_validator],
        help_text=_("مكون من 14 رقماً.")
    )
    
    role = models.CharField(
        _('نوع المستخدم'),
        max_length=1, 
        choices=Role.choices, 
        default=Role.STUDENT,
        db_index=True 
    )

    is_verified = models.BooleanField(
        _('حالة التوثيق'),
        default=False, 
        help_text=_("تشير إلى ما إذا كان المستخدم قد قام بتفعيل البريد الإلكتروني.")
    )
    
    image = models.ImageField(
        _('صورة الملف الشخصي'),
        upload_to='profile_images/%Y/%m/',
        null=True,
        blank=True,
        validators=[validate_signature_image],
        help_text=_("صورة شخصية للمستخدم (اختياري)")
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'national_id']

    objects = UserManager()

    class Meta:
        verbose_name = _('مستخدم')
        verbose_name_plural = _('المستخدمين')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email', 'national_id']),
            models.Index(fields=['role', 'is_verified']),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            local, domain = self.email.split('@')
            self.email = f"{local.upper()}@{domain.lower()}"
            
        if self.pk:
            try:
                old = User.objects.get(pk=self.pk)
            except User.DoesNotExist:
                old = None
        else:
            old = None
        super().save(*args, **kwargs)
    
    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else self.email
    
    def __str__(self):
        return f"{self.full_name} - ({self.get_role_display()})"


# --- Program Model ---
class Program(models.Model):
    name = models.CharField(_("اسم القسم / البرنامج"), max_length=100, unique=True)
    code = models.CharField(_("كود البرنامج"), max_length=10, unique=True, help_text=_("مثال: CS, BIO, MATH"))
    description = models.TextField(_("وصف البرنامج"), blank=True)
    is_active = models.BooleanField(_("متاح حالياً"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("برنامج أكاديمي")
        verbose_name_plural = _("البرامج الأكاديمية")
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - ({self.code})"


# --- Student Profile ---
class StudentProfile(RoleValidatedProfileMixin, models.Model):
    class Level(models.IntegerChoices):
        LEVEL_1 = 1, _('المستوى الأول')
        LEVEL_2 = 2, _('المستوى الثاني')
        LEVEL_3 = 3, _('المستوى الثالث')
        LEVEL_4 = 4, _('المستوى الرابع')

    required_role = UserRoles.STUDENT

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='student_profile',
        verbose_name=_("حساب المستخدم"),
        limit_choices_to={'role': UserRoles.STUDENT}
    )
    
    program = models.ForeignKey(
        Program, 
        on_delete=models.PROTECT, 
        related_name='students',
        verbose_name=_("القسم الأكاديمي"),
        help_text=_("القسم الدراسي الذي يتبعه الطالب"),
        null=True,
        blank=True,
    )

    student_id = models.CharField(
        _("الرقم الجامعي"), 
        max_length=20, 
        unique=True,
        db_index=True
    )

    level = models.IntegerField(
        _("المستوى الدراسي"),
        choices=Level.choices,
        default=Level.LEVEL_1
    )

    gpa = models.DecimalField(
        _("المعدل التراكمي (GPA)"),
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00), MaxValueValidator(4.00)],
    )

    phone = models.CharField(
        _("رقم الموبايل المصري"), 
        validators=[egyptian_phone_validator], 
        max_length=11,
        unique=True,
        help_text=_("مثال: 010xxxxxxxx")
    )
    
    address = models.TextField(_("عنوان السكن بالتفصيل"), blank=True)
    
    disability_status = models.BooleanField(
        _("ذوي الاحتياجات الخاصة"), 
        default=False
    )
    
    HasPreviousSupport	= models.BooleanField(
        _("هل حصلت على دعم سابق؟"),
        default=False,
    )

    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("آخر تحديث"), auto_now=True)

    class Meta:
        verbose_name = _("ملف الطالب")
        verbose_name_plural = _("ملفات الطلاب")
        ordering = ['-gpa', 'student_id']
        indexes = [
            models.Index(fields=['program', 'level']),
            models.Index(fields=['gpa']),
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.student_id}"

    @property
    def academic_standing(self) -> str:
        if self.gpa >= 3.5: 
            return _("امتياز")
        if self.gpa >= 3.0: 
            return _("جيد جداً")
        if self.gpa >= 2.5: 
            return _("جيد")
        if self.gpa >= 2.0: 
            return _("مقبول")
        return _("إنذار أكاديمي")


# --- Reviewer Profile ---
class ReviewerProfile(RoleValidatedProfileMixin, models.Model):
    class AcademicRank(models.TextChoices):
        PROFESSOR = 'PROF', _('أستاذ دكتور')
        ASSOCIATE_PROF = 'ASSOC', _('أستاذ مشارك')
        ASSISTANT_PROF = 'ASST', _('أستاذ مساعد')
        LECTURER = 'LECT', _('مدرس / محاضر')

    required_role = UserRoles.REVIEWER

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviewer_profile',
        verbose_name=_("حساب المستخدم"),
        limit_choices_to={'role': UserRoles.REVIEWER}
    )

    academic_rank = models.CharField(
        _("الدرجة العلمية"),
        max_length=5,
        choices=AcademicRank.choices,
        default=AcademicRank.LECTURER
    )

    specialization = models.CharField(
        _("التخصص الدقيق"), 
        max_length=100,
        help_text=_("مثال: الكيمياء العضوية، فيزياء الجوامد")
    )

    assigned_programs = models.ManyToManyField(
        Program,
        related_name='reviewers',
        verbose_name=_("الأقسام المسئول عن مراجعتها"),
        blank=True
    )

    bio = models.TextField(_("نبذة مختصرة"), blank=True)
    office_location = models.CharField(_("مقر المكتب"), max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("ملف المُراجع")
        verbose_name_plural = _("ملفات المُراجعين")
        indexes = [
            models.Index(fields=['user', 'academic_rank']),
            models.Index(fields=['specialization']),
        ]

    def __str__(self):
        return f"{self.get_academic_rank_display()} / {self.user.full_name}"


# --- Committee Head Profile ---
class CommitteeHeadProfile(RoleValidatedProfileMixin, models.Model):
    required_role = UserRoles.COMMITTEE_HEAD

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='committee_head_profile',
        verbose_name=_("حساب المستخدم"),
        limit_choices_to={'role': UserRoles.COMMITTEE_HEAD}
    )

    committee_name = models.CharField(
        _("اسم اللجنة"), 
        max_length=150,
        help_text=_("مثال: لجنة المساعدات المالية، لجنة شؤون الطلاب")
    )

    authority_level = models.PositiveSmallIntegerField(
        _("مستوى الصلاحية"),
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_("مستوى الإدارة (1 هو الأدنى، 5 هو الأعلى)")
    )

    managed_programs = models.ManyToManyField(
        Program,
        related_name='committee_heads',
        verbose_name=_("الأقسام المشرف عليها"),
        blank=True,
        help_text=_("الأقسام الأكاديمية التي تندرج تحت اختصاص هذه اللجنة")
    )

    signature_image = models.ImageField(
        _("صورة التوقيع الرسمي"),
        upload_to='signatures/heads/%Y/%m/',
        validators=[validate_signature_image],
        null=True,
        blank=True,
        help_text=_("تُستخدم لاعتماد المستندات إلكترونياً (PNG أو JPG، بحد أقصى 5MB)")
    )

    is_active_head = models.BooleanField(_("رئيس لجنة حالي"), default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("ملف رئيس اللجنة")
        verbose_name_plural = _("ملفات رؤساء اللجان")
        indexes = [
            models.Index(fields=['is_active_head', 'authority_level']),
            models.Index(fields=['committee_name']),
        ]

    def __str__(self):
        return f"رئيس {self.committee_name}: {self.user.full_name}"

    def clean(self):
        super().clean()
        if not self.user.is_staff:
            raise ValidationError(_("رئيس اللجنة يجب أن يكون من فريق العمل (is_staff=True)."))

class AuditorProfile(RoleValidatedProfileMixin, models.Model):
    required_role = UserRoles.AUDITOR

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='auditor_profile',
        verbose_name=_("حساب المستخدم"),
        limit_choices_to={'role': UserRoles.AUDITOR}
    )

    assigned_programs = models.ManyToManyField(
        Program,
        related_name='auditors',
        verbose_name=_("الأقسام المسئول عن تدقيقها"),
        blank=True
    )

    bio = models.TextField(_("نبذة مختصرة"), blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("ملف المراقب")
        verbose_name_plural = _("ملفات المراقبين")
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"المراقب: {self.user.full_name}"