import uuid
from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from accounts.models import SerialCounter, StudentProfile, UserRoles


def validate_financial_data(value):
    required_keys = [
        "father_income",
        "mother_income",
        "family_members",
        "housing_status",
    ]
    if not all(key in value for key in required_keys):
        raise ValidationError(_("بيانات التقييم المالي غير مكتملة."))


# ==============================
# SupportCycle
# ==============================
class SupportCycle(models.Model):

    SEMESTER_CHOICES = [
        ("FIRST", _("الفصل الأول")),
        ("SECOND", _("الفصل الثاني")),
        ("SUMMER", _("الفصل الصيفي")),
    ]

    STATUS_CHOICES = [
        ("DRAFT", _("مسودة")),
        ("OPEN", _("مفتوح للتقديم")),
        ("UNDER_REVIEW", _("قيد المراجعة")),
        ("CLOSED", _("مغلق")),
        ("ARCHIVED", _("مؤرشف")),
    ]

    cycle_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, verbose_name=_("معرّف الدورة")
    )
    serial_number = models.CharField(
        max_length=20, unique=True, blank=True, default="", verbose_name=_("رقم الدورة")
    )
    name = models.CharField(max_length=255, verbose_name=_("اسم الدورة"))
    academic_year = models.CharField(max_length=20, verbose_name=_("العام الدراسي"))
    semester = models.CharField(
        max_length=10, choices=SEMESTER_CHOICES, verbose_name=_("الفصل الدراسي")
    )
    total_budget = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name=_("إجمالي الميزانية")
    )
    reserved_budget = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name=_("الميزانية المحجوزة")
    )
    disbursed_budget = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name=_("الميزانية المصروفة")
    )
    application_start_date = models.DateTimeField(verbose_name=_("تاريخ بداية التقديم"))
    application_end_date = models.DateTimeField(verbose_name=_("تاريخ نهاية التقديم"))
    review_start_date = models.DateTimeField(
        null=True, blank=True, verbose_name=_("تاريخ بداية المراجعة")
    )
    review_end_date = models.DateTimeField(
        null=True, blank=True, verbose_name=_("تاريخ نهاية المراجعة")
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="DRAFT", verbose_name=_("الحالة")
    )
    scoring_rules_snapshot = models.JSONField(
        default=list, blank=True, verbose_name=_("نسخة قواعد التقييم")
    )
    is_locked = models.BooleanField(default=False, verbose_name=_("مقفلة"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_cycles",
        verbose_name=_("تم الإنشاء بواسطة"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("تاريخ الإنشاء")
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("آخر تحديث"))

    # ==============================
    # Properties
    # ==============================
    @property
    def available_budget(self):
        return self.total_budget - self.reserved_budget - self.disbursed_budget

    @property
    def is_open_for_application(self):
        now = timezone.now()
        return (
            self.status == "OPEN"
            and not self.is_locked
            and self.application_start_date <= now <= self.application_end_date
        )

    @property
    def is_open_for_review(self):
        if not self.review_start_date or not self.review_end_date:
            return False
        now = timezone.now()
        return (
            self.status == "UNDER_REVIEW"
            and not self.is_locked
            and self.review_start_date <= now <= self.review_end_date
        )

    # ==============================
    # Validation
    # ==============================
    def clean(self):
        errors = {}

        if self.application_start_date and self.application_end_date:
            if self.application_start_date >= self.application_end_date:
                errors["application_end_date"] = _(
                    "تاريخ نهاية التقديم يجب أن يكون بعد تاريخ البداية."
                )

        if self.review_start_date and self.review_end_date:
            if self.review_start_date >= self.review_end_date:
                errors["review_end_date"] = _(
                    "تاريخ نهاية المراجعة يجب أن يكون بعد تاريخ بداية المراجعة."
                )
            if (
                self.application_end_date
                and self.review_start_date <= self.application_end_date
            ):
                errors["review_start_date"] = _(
                    "يجب أن تبدأ فترة المراجعة بعد انتهاء فترة تقديم الطلبات."
                )

        if self.total_budget is not None:
            reserved = self.reserved_budget or 0
            disbursed = self.disbursed_budget or 0
            if (reserved + disbursed) > self.total_budget:
                errors["reserved_budget"] = _(
                    "إجمالي الميزانية المحجوزة والمصروفة (%(total)s) "
                    "أكبر من الميزانية الكلية (%(budget)s)."
                ) % {"total": reserved + disbursed, "budget": self.total_budget}

        if errors:
            raise ValidationError(errors)

    # ==============================
    # Save & Serial Generation
    # ==============================
    def generate_serial(self):
        with transaction.atomic():
            year = timezone.now().year
            count = (
                SupportCycle.objects.select_for_update()
                .filter(created_at__year=year)
                .count()
                + 1
            )
            return f"دورة-{year}-{str(count).zfill(5)}"

    def save(self, *args, **kwargs):
        if not kwargs.get("update_fields"):
            self.full_clean()

        if not self.serial_number:
            self.serial_number = self.generate_serial()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.serial_number or _('بدون رقم')})"

    class Meta:
        verbose_name = _("دورة دعم")
        verbose_name_plural = _("دورات الدعم")
        ordering = ["-created_at"]


# ==============================
# AidApplication
# ==============================
class AidApplication(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", _("مسودة")),
        ("SUBMITTED", _("تم التقديم")),
        ("UNDER_REVIEW", _("قيد المراجعة")),
        ("SCORED", _("تم التقييم")),
        ("APPROVED", _("مقبول")),
        ("REJECTED", _("مرفوض")),
        ("DISBURSED", _("تم الصرف")),
    ]

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_("المعرف")
    )
    serial_number = models.CharField(
        max_length=50, unique=True, blank=True, default="", verbose_name=_("رقم الطلب")
    )
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="applications",
        verbose_name=_("الطالب"),
    )
    cycle = models.ForeignKey(
        "SupportCycle",
        on_delete=models.CASCADE,
        related_name="applications",
        verbose_name=_("دورة الدعم"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="DRAFT", verbose_name=_("الحالة")
    )
    supporting_document = models.FileField(
        upload_to="aid_applications/documents/%Y/",
        validators=[FileExtensionValidator(["pdf"])],
        null=True,
        blank=True,
        verbose_name=_("المستندات الداعمة (PDF)"),
    )
    financial_assessment = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_financial_data],
        verbose_name=_("التقييم المالي"),
    )
    committee_decision = models.TextField(blank=True, verbose_name=_("قرار اللجنة"))
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name=_("عنوان IP")
    )
    user_agent = models.TextField(blank=True, verbose_name=_("معلومات المتصفح"))
    submission_date = models.DateTimeField(
        null=True, blank=True, verbose_name=_("تاريخ التقديم")
    )
    decision_date = models.DateTimeField(
        null=True, blank=True, verbose_name=_("تاريخ القرار")
    )
    deleted_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("تاريخ الحذف")
    )
    is_locked = models.BooleanField(default=False, verbose_name=_("مقفل"))
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("تاريخ الإنشاء")
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("آخر تحديث"))

    profile_snapshot = models.JSONField(default=dict, blank=True)

    def freeze_student_data(self):
        profile = self.student

        self.profile_snapshot = {
            "gpa": str(profile.gpa),
            "level": profile.level,
            "program": {
                "id": profile.program.id if profile.program else None,
                "name": profile.program.name if profile.program else "N/A",
            },
            "disability_status": profile.disability_status,
        }

        self.save(update_fields=["profile_snapshot"])

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def generate_serial(self):
        with transaction.atomic():
            year = timezone.now().year
            counter_key = f"application_{year}"

            counter, created = SerialCounter.objects.get_or_create(key=counter_key)
            counter = SerialCounter.objects.select_for_update().get(key=counter_key)

            counter.last_value += 1
            counter.save()

            return f"طلب-{year}-{str(counter.last_value).zfill(5)}"

    @staticmethod
    def _extract_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def submit(self, request=None):
        if self.status != "DRAFT":
            raise ValidationError(_("يمكن فقط تقديم الطلبات في حالة 'مسودة'."))

        if self.is_deleted:
            raise ValidationError(_("لا يمكن تقديم طلب محذوف."))

        if self.is_locked:
            raise ValidationError(_("هذا الطلب مقفل ولا يمكن تعديله أو تقديمه."))

        if not self.cycle.is_open_for_application:
            raise ValidationError(_("فترة التقديم غير متاحة حالياً."))

        self.status = "SUBMITTED"
        self.submission_date = timezone.now()
        self.serial_number = self.generate_serial()

        if request:
            self.ip_address = self._extract_ip(request)
            self.user_agent = request.META.get("HTTP_USER_AGENT", "")

        self.full_clean()
        self.save()

    def soft_delete(self):
        if self.is_deleted:
            raise ValidationError(_("تم حذف هذا الطلب بالفعل."))

        if self.status in ("APPROVED", "DISBURSED"):
            raise ValidationError(_("لا يمكن حذف طلب تم قبوله أو صرفه."))

        with transaction.atomic():
            for allocation in self.allocations.filter(status="PENDING"):
                allocation.cancel()
            self.deleted_at = timezone.now()
            self.save(update_fields=["deleted_at", "updated_at"])

    def __str__(self):
        return self.serial_number or _("طلب غير مكتمل (%(id)s)") % {"id": self.id}

    def can_transition_to(self, new_status):
        current = self.status

        allowed_transitions = {
            "DRAFT": ["SUBMITTED"],  # المسودة تذهب للتقديم فقط
            "SUBMITTED": [
                "UNDER_REVIEW",
                "DRAFT",
            ],  # المقدم يراجع أو يعاد لمسودة (بقرار أدمن)
            "UNDER_REVIEW": ["SCORED"],  # تحت المراجعة تذهب للتقييم
            "SCORED": ["APPROVED", "REJECTED"],  # التقييم ينتهي بقبول أو رفض
            "APPROVED": ["DISBURSED"],  # المقبول يذهب للصرف
            "REJECTED": ["DRAFT"],  # المرفوض قد يسمح له بالتعديل في دورة أخرى
        }

        return new_status in allowed_transitions.get(current, [])

    def transition_to(self, new_status, user=None):
        if not self.can_transition_to(new_status):
            raise ValidationError(
                f"لا يمكن الانتقال من {self.get_status_display()} إلى {new_status}"
            )

        self.status = new_status
        if new_status == "SUBMITTED":
            self.submission_date = timezone.now()
        elif new_status in ["APPROVED", "REJECTED"]:
            self.decision_date = timezone.now()

        self.save()

    class Meta:
        verbose_name = _("طلب مساعدة")
        verbose_name_plural = _("طلبات المساعدة")
        ordering = ["-created_at"]
        unique_together = [["student", "cycle"]]
        indexes = [
            models.Index(fields=["student", "cycle"]),
            models.Index(fields=["status"]),
            models.Index(fields=["submission_date"]),
        ]


# ==============================
# ScoringRule
# ==============================
class ScoringRule(models.Model):

    CRITERIA_CHOICES = [
        ("INCOME_TIER", _("شريحة الدخل")),
        ("FAMILY_SIZE", _("عدد أفراد الأسرة")),
        ("GPA", _("المعدل التراكمي")),
        ("SPECIAL_CASES", _("الحالات الخاصة")),
        ("SOCIAL_RESEARCH", _("البحث الاجتماعي")),
    ]

    rule_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, verbose_name=_("معرّف القاعدة")
    )
    cycle = models.ForeignKey(
        SupportCycle,
        on_delete=models.CASCADE,
        related_name="rules",
        verbose_name=_("دورة الدعم"),
    )
    criteria_type = models.CharField(
        max_length=30, choices=CRITERIA_CHOICES, verbose_name=_("نوع المعيار")
    )
    condition = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("شرط التطبيق"), help_text=_("مثال: {'min': 0, 'max': 3000}")
    )
    description = models.TextField(blank=True, verbose_name=_("وصف القاعدة"))
    points = models.IntegerField(verbose_name=_("عدد النقاط"))
    weight = models.DecimalField(
        max_digits=4, decimal_places=2, default=1.0, verbose_name=_("الوزن")
    )
    priority = models.IntegerField(default=0, verbose_name=_("الأولوية"))
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))

    def clean(self):
        errors = {}

        if self.weight is not None and self.weight <= 0:
            errors["weight"] = _("الوزن يجب أن يكون أكبر من صفر.")

        if self.points is not None and self.points < 0:
            errors["points"] = _("النقاط لا يمكن أن تكون سالبة.")

        if self.criteria_type == "INCOME_TIER":
            if not isinstance(self.condition, dict) or not (
                "min" in self.condition or "max" in self.condition
            ):
                errors["condition"] = _("يجب تحديد min أو max لشريحة الدخل.")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return _("%(criteria)s — %(points)s نقطة (وزن: %(weight)s)") % {
            "criteria": self.get_criteria_type_display(),
            "points": self.points,
            "weight": self.weight,
        }

    class Meta:
        verbose_name = _("قاعدة تقييم")
        verbose_name_plural = _("قواعد التقييم")
        ordering = ["priority"]
        unique_together = [["cycle", "criteria_type"]]
        indexes = [models.Index(fields=["cycle", "criteria_type", "is_active"])]


# ==============================
# CommitteeReview
# ==============================
class CommitteeReview(models.Model):

    REVIEW_STATUS_CHOICES = [
        ("DRAFT", _("مسودة")),
        ("SUBMITTED", _("تم التقديم")),
    ]

    review_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, verbose_name=_("معرّف المراجعة")
    )
    application = models.ForeignKey(
        AidApplication,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("الطلب"),
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="committee_reviews",
        verbose_name=_("المراجع"),
        limit_choices_to={"role": UserRoles.REVIEWER},
    )
    status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default="DRAFT",
        verbose_name=_("حالة المراجعة"),
    )
    conflict_of_interest = models.BooleanField(
        default=False, verbose_name=_("تعارض مصالح")
    )
    dimension_scores = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("درجات التقييم"),
        help_text=_("مثال: {'income_tier': 10, 'gpa': 5}"),
    )
    total_score = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name=_("المجموع الكلي")
    )
    qualitative_notes = models.TextField(blank=True, verbose_name=_("ملاحظات نوعية"))
    review_timestamp = models.DateTimeField(
        auto_now_add=True, verbose_name=_("وقت المراجعة")
    )
    is_submitted = models.BooleanField(default=False, verbose_name=_("تم التقديم"))

    @property
    def is_finalized(self):
        return self.status == "SUBMITTED"

    def clean(self):
        if self.is_submitted and not self.conflict_of_interest and not self.dimension_scores:
            raise ValidationError(_("لا يمكن تقديم مراجعة بدون درجات تقييم."))

    def calculate_total(self):
        if self.conflict_of_interest:
            self.total_score = 0
            return
        cycle = self.application.cycle
        rules = ScoringRule.objects.filter(cycle=cycle, is_active=True)
        weight_map = {rule.criteria_type.lower(): float(rule.weight) for rule in rules}
        self.total_score = sum(
            float(score) * weight_map.get(dimension.lower(), 1.0)
            for dimension, score in self.dimension_scores.items()
        )

    def submit(self):
        if self.is_submitted:
            raise ValidationError(_("هذه المراجعة مقدّمة بالفعل."))
        if not self.conflict_of_interest and not self.dimension_scores:
            raise ValidationError(_("لا يمكن تقديم مراجعة بدون درجات تقييم."))

        self.calculate_total()
        self.is_submitted = True
        self.status = "SUBMITTED"

        self.save(update_fields=["total_score", "is_submitted", "status", "updated_at"])

    def save(self, *args, **kwargs):
        if not kwargs.get("update_fields"):
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return _("مراجعة — %(app)s (النتيجة: %(score)s)") % {
            "app": self.application,
            "score": self.total_score,
        }

    class Meta:
        verbose_name = _("مراجعة لجنة")
        verbose_name_plural = _("مراجعات اللجنة")
        ordering = ["-review_timestamp"]
        unique_together = [["application", "reviewer"]]


# ==============================
# BudgetAllocation
# ==============================
class BudgetAllocation(models.Model):

    STATUS_CHOICES = [
        ("PENDING", _("قيد الانتظار")),
        ("DISBURSED", _("تم الصرف")),
        ("CANCELLED", _("ملغي")),
    ]

    allocation_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, verbose_name=_("معرّف التخصيص")
    )
    cycle = models.ForeignKey(
        SupportCycle,
        on_delete=models.CASCADE,
        related_name="allocations",
        verbose_name=_("دورة الدعم"),
    )
    application = models.ForeignKey(
        AidApplication,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="allocations",
        verbose_name=_("الطلب"),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
        verbose_name=_("الحالة"),
    )
    amount_allocated = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("المبلغ المخصص")
    )
    amount_disbursed = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name=_("المبلغ المصروف")
    )
    disbursement_date = models.DateField(
        null=True, blank=True, verbose_name=_("تاريخ الصرف")
    )
    disbursed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disbursed_allocations",
        verbose_name=_("تم الصرف بواسطة"),
    )
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات"))
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("تاريخ الإنشاء")
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("آخر تحديث"))

    @property
    def remaining_amount(self):
        return self.amount_allocated - self.amount_disbursed

    def clean(self):
        errors = {}

        if self.amount_allocated is not None and self.cycle_id:
            with transaction.atomic():
                current_cycle = SupportCycle.objects.select_for_update().get(
                    pk=self.cycle_id
                )

                adjustment = self.amount_allocated
                if self.pk:
                    old_allocation = BudgetAllocation.objects.filter(pk=self.pk).first()
                    if old_allocation:
                        adjustment -= old_allocation.amount_allocated

                available_capacity = (
                    current_cycle.total_budget
                    - current_cycle.reserved_budget
                    - current_cycle.disbursed_budget
                )

                if adjustment > available_capacity:
                    errors["amount_allocated"] = _(
                        "المبلغ (%(amount)s) يتجاوز الميزانية المتاحة (%(available)s)."
                    ) % {
                        "amount": self.amount_allocated,
                        "available": available_capacity,
                    }

        if (
            self.amount_disbursed is not None
            and self.amount_allocated is not None
            and self.amount_disbursed > self.amount_allocated
        ):
            errors["amount_disbursed"] = _("المبلغ المصروف لا يمكن أن يتجاوز المخصص.")

        amount_disbursed = self.amount_disbursed or 0

        if self.disbursement_date and amount_disbursed <= 0:
            errors["disbursement_date"] = _("لا يمكن تحديد تاريخ بدون مبلغ مصروف.")

        if amount_disbursed > 0 and not self.disbursement_date:
            errors["disbursement_date"] = _("يجب تحديد تاريخ الصرف.")

        if self.application_id and self.application:
            if self.application.status not in ("APPROVED", "DISBURSED"):
                errors["application"] = _("يمكن التخصيص فقط للطلبات المقبولة.")

        if errors:
            raise ValidationError(errors)

    def disburse(self, amount, disbursement_date=None, disbursed_by=None):
        if self.status == "CANCELLED":
            raise ValidationError(_("لا يمكن الصرف على تخصيص ملغي."))

        if self.status == "DISBURSED":
            raise ValidationError(_("تم الصرف بالفعل."))

        if amount <= 0:
            raise ValidationError(_("مبلغ الصرف يجب أن يكون أكبر من صفر."))

        if amount > self.amount_allocated:
            raise ValidationError(
                _("المبلغ (%(amount)s) أكبر من المخصص (%(allocated)s).")
                % {
                    "amount": amount,
                    "allocated": self.amount_allocated,
                }
            )

        with transaction.atomic():
            old_status = self.status
            cycle = SupportCycle.objects.select_for_update().get(pk=self.cycle_id)

            if old_status == "PENDING":
                cycle.reserved_budget -= self.amount_allocated

            self.amount_disbursed = amount
            self.disbursement_date = disbursement_date or timezone.now().date()
            self.disbursed_by = disbursed_by
            self.status = "DISBURSED"

            cycle.disbursed_budget += amount
            cycle.save(update_fields=["reserved_budget", "disbursed_budget", "updated_at"])

            self.full_clean()
            self.save(
                update_fields=[
                    "amount_disbursed",
                    "disbursement_date",
                    "disbursed_by",
                    "status",
                    "updated_at",
                ]
            )

    def cancel(self):
        if self.status == "DISBURSED":
            raise ValidationError(_("لا يمكن إلغاء بعد الصرف."))

        if self.status == "CANCELLED":
            raise ValidationError(_("التخصيص ملغي بالفعل."))

        with transaction.atomic():
            if self.status == "PENDING":
                cycle = SupportCycle.objects.select_for_update().get(pk=self.cycle_id)
                cycle.reserved_budget -= self.amount_allocated
                cycle.save(update_fields=["reserved_budget", "updated_at"])

            self.status = "CANCELLED"
            self.save(update_fields=["status", "updated_at"])

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_allocation = None
        if not is_new:
            old_allocation = BudgetAllocation.objects.filter(pk=self.pk).first()

        if not kwargs.get("update_fields"):
            self.full_clean()
            
        with transaction.atomic():
            cycle = SupportCycle.objects.select_for_update().get(pk=self.cycle_id)
            if is_new:
                if self.status == "PENDING":
                    cycle.reserved_budget += self.amount_allocated
                elif self.status == "DISBURSED":
                    cycle.disbursed_budget += self.amount_allocated
                cycle.save(update_fields=["reserved_budget", "disbursed_budget", "updated_at"])
            elif not is_new and old_allocation:
                if old_allocation.status == "PENDING" and self.status == "PENDING":
                    diff = self.amount_allocated - old_allocation.amount_allocated
                    if diff != 0:
                        cycle.reserved_budget += diff
                        cycle.save(update_fields=["reserved_budget", "updated_at"])
            
            super().save(*args, **kwargs)

    def __str__(self):
        return _("%(app)s — %(amount)s [%(status)s]") % {
            "app": self.application,
            "amount": self.amount_allocated,
            "status": self.get_status_display(),
        }

    class Meta:
        verbose_name = _("تخصيص ميزانية")
        verbose_name_plural = _("تخصيصات الميزانية")
        ordering = ["-created_at"]
