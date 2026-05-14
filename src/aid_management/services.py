"""
محرك التقييم التلقائي (Auto-Scoring Engine)
============================================
يقوم بربط بيانات الطالب المالية والأكاديمية بقواعد التقييم المحددة في الدورة
ويحسب درجة أولية تلقائية لكل طلب.

المنطق:
- INCOME_TIER: يحسب إجمالي دخل الأسرة ويقارنه بـ condition {min, max}
- FAMILY_SIZE: يقارن عدد أفراد الأسرة بـ condition {min, max}
- GPA: يقارن المعدل التراكمي بـ condition {min, max}
- SPECIAL_CASES: يتحقق من حالة الإعاقة (disability_status)
- SOCIAL_RESEARCH: لا يُحسب تلقائياً — يحتاج تقييم يدوي
"""

import logging
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass, field
from typing import Optional

from .models import ScoringRule, AidApplication

logger = logging.getLogger(__name__)


@dataclass
class DimensionResult:
    """نتيجة تقييم بُعد واحد."""
    criteria_type: str
    criteria_display: str
    raw_value: Optional[str]  # القيمة المستخرجة من بيانات الطالب
    awarded_points: int       # النقاط الممنوحة
    max_points: int           # أقصى نقاط ممكنة
    weight: float             # الوزن المطبّق
    weighted_score: float     # النقاط × الوزن
    matched: bool             # هل تطابق الشرط؟
    reason: str               # تفسير النتيجة
    is_auto: bool = True      # هل تم حسابه تلقائياً؟


@dataclass
class ScoringResult:
    """نتيجة التقييم الكامل لطلب واحد."""
    application_id: str
    total_auto_score: float = 0.0
    max_possible_score: float = 0.0
    dimensions: list = field(default_factory=list)
    has_manual_dimensions: bool = False  # هل يوجد أبعاد تحتاج تقييم يدوي؟

    @property
    def score_percentage(self):
        if self.max_possible_score == 0:
            return 0
        return round((self.total_auto_score / self.max_possible_score) * 100, 1)

    @property
    def auto_dimensions(self):
        return [d for d in self.dimensions if d.is_auto]

    @property
    def manual_dimensions(self):
        return [d for d in self.dimensions if not d.is_auto]


class ScoringEngine:
    """
    محرك التقييم التلقائي.
    يأخذ طلباً ويقيّمه بناءً على قواعد الدورة المرتبطة.
    """

    # الأبعاد التي لا يمكن تقييمها تلقائياً
    MANUAL_CRITERIA = {'SOCIAL_RESEARCH'}

    def __init__(self, application: AidApplication):
        self.application = application
        self.cycle = application.cycle
        self.student = application.student
        self.financial_data = application.financial_assessment or {}
        self.rules = list(
            ScoringRule.objects.filter(
                cycle=self.cycle,
                is_active=True
            ).order_by('priority')
        )

    def evaluate(self) -> ScoringResult:
        """
        تقييم الطلب بالكامل وإرجاع النتيجة التفصيلية.
        """
        result = ScoringResult(application_id=str(self.application.id))

        for rule in self.rules:
            dimension = self._evaluate_rule(rule)
            result.dimensions.append(dimension)

            if dimension.is_auto:
                result.total_auto_score += dimension.weighted_score
            else:
                result.has_manual_dimensions = True

            result.max_possible_score += rule.points * float(rule.weight)

        return result

    def get_suggested_scores(self) -> dict:
        """
        إرجاع قاموس بالدرجات المقترحة لكل بُعد (للاستخدام في واجهة المراجع).
        المفتاح هو criteria_type.lower() والقيمة هي النقاط المقترحة.
        """
        scoring_result = self.evaluate()
        suggestions = {}
        for dim in scoring_result.dimensions:
            key = dim.criteria_type.lower()
            suggestions[key] = {
                'suggested_points': dim.awarded_points,
                'max_points': dim.max_points,
                'raw_value': dim.raw_value,
                'reason': dim.reason,
                'is_auto': dim.is_auto,
                'matched': dim.matched,
            }
        return suggestions

    def _evaluate_rule(self, rule: ScoringRule) -> DimensionResult:
        """تقييم قاعدة واحدة."""
        criteria = rule.criteria_type

        if criteria in self.MANUAL_CRITERIA:
            return self._manual_dimension(rule)

        evaluator_map = {
            'INCOME_TIER': self._evaluate_income_tier,
            'FAMILY_SIZE': self._evaluate_family_size,
            'GPA': self._evaluate_gpa,
            'SPECIAL_CASES': self._evaluate_special_cases,
        }

        evaluator = evaluator_map.get(criteria)
        if evaluator:
            return evaluator(rule)

        # نوع غير معروف
        logger.warning(f"نوع معيار غير معروف: {criteria}")
        return DimensionResult(
            criteria_type=criteria,
            criteria_display=rule.get_criteria_type_display(),
            raw_value=None,
            awarded_points=0,
            max_points=rule.points,
            weight=float(rule.weight),
            weighted_score=0,
            matched=False,
            reason="نوع معيار غير مدعوم للتقييم التلقائي.",
            is_auto=False,
        )

    def _evaluate_income_tier(self, rule: ScoringRule) -> DimensionResult:
        """
        تقييم شريحة الدخل.
        يحسب إجمالي دخل الأسرة (أب + أم) ويقارنه بالشرط.
        كلما كان الدخل أقل، كلما زادت النقاط (عكسي).
        """
        father_income = self._safe_decimal(self.financial_data.get('father_income', 0))
        mother_income = self._safe_decimal(self.financial_data.get('mother_income', 0))
        total_income = father_income + mother_income

        condition = rule.condition or {}
        cond_min = self._safe_decimal(condition.get('min', 0))
        cond_max = self._safe_decimal(condition.get('max', float('inf')))

        matched = cond_min <= total_income <= cond_max

        if matched:
            # منطق عكسي: الدخل الأقل يحصل على نقاط أكثر
            if cond_max > cond_min and cond_max != Decimal('inf'):
                income_range = float(cond_max - cond_min)
                position = float(total_income - cond_min)
                # النسبة العكسية: كلما كان الدخل أقل، كلما زادت النسبة
                inverse_ratio = 1.0 - (position / income_range) if income_range > 0 else 1.0
                awarded = round(rule.points * inverse_ratio)
            else:
                awarded = rule.points
        else:
            # خارج النطاق — إذا كان الدخل أقل من الحد الأدنى يحصل على كل النقاط
            if total_income < cond_min:
                awarded = rule.points
                matched = True
            else:
                awarded = 0

        return DimensionResult(
            criteria_type=rule.criteria_type,
            criteria_display=rule.get_criteria_type_display(),
            raw_value=f"{total_income} ج.م",
            awarded_points=awarded,
            max_points=rule.points,
            weight=float(rule.weight),
            weighted_score=awarded * float(rule.weight),
            matched=matched,
            reason=self._income_reason(total_income, cond_min, cond_max, matched),
        )

    def _evaluate_family_size(self, rule: ScoringRule) -> DimensionResult:
        """
        تقييم عدد أفراد الأسرة.
        كلما زاد العدد، زادت النقاط (طردي).
        """
        family_members = self._safe_int(self.financial_data.get('family_members', 0))

        condition = rule.condition or {}
        cond_min = self._safe_int(condition.get('min', 0))
        cond_max = self._safe_int(condition.get('max', 20))

        matched = cond_min <= family_members <= cond_max

        if matched:
            # منطق طردي: الأسرة الأكبر تحصل على نقاط أكثر
            if cond_max > cond_min:
                family_range = cond_max - cond_min
                position = family_members - cond_min
                ratio = position / family_range if family_range > 0 else 1.0
                awarded = round(rule.points * ratio)
            else:
                awarded = rule.points
        else:
            if family_members > cond_max:
                awarded = rule.points
                matched = True
            else:
                awarded = 0

        return DimensionResult(
            criteria_type=rule.criteria_type,
            criteria_display=rule.get_criteria_type_display(),
            raw_value=f"{family_members} فرد",
            awarded_points=awarded,
            max_points=rule.points,
            weight=float(rule.weight),
            weighted_score=awarded * float(rule.weight),
            matched=matched,
            reason=f"عدد أفراد الأسرة: {family_members} (النطاق: {cond_min}-{cond_max}).",
        )

    def _evaluate_gpa(self, rule: ScoringRule) -> DimensionResult:
        """
        تقييم المعدل التراكمي.
        كلما كان المعدل أعلى، زادت النقاط (طردي).
        """
        gpa = float(self.student.gpa)

        condition = rule.condition or {}
        cond_min = float(condition.get('min', 0))
        cond_max = float(condition.get('max', 4.0))

        matched = cond_min <= gpa <= cond_max

        if matched:
            # منطق طردي: المعدل الأعلى يحصل على نقاط أكثر
            if cond_max > cond_min:
                gpa_range = cond_max - cond_min
                position = gpa - cond_min
                ratio = position / gpa_range if gpa_range > 0 else 1.0
                awarded = round(rule.points * ratio)
            else:
                awarded = rule.points
        else:
            if gpa > cond_max:
                awarded = rule.points
                matched = True
            else:
                awarded = 0

        return DimensionResult(
            criteria_type=rule.criteria_type,
            criteria_display=rule.get_criteria_type_display(),
            raw_value=f"{gpa:.2f}",
            awarded_points=awarded,
            max_points=rule.points,
            weight=float(rule.weight),
            weighted_score=awarded * float(rule.weight),
            matched=matched,
            reason=f"المعدل التراكمي: {gpa:.2f} / 4.00 (النطاق: {cond_min}-{cond_max}).",
        )

    def _evaluate_special_cases(self, rule: ScoringRule) -> DimensionResult:
        """
        تقييم الحالات الخاصة (ذوي الاحتياجات الخاصة).
        """
        has_disability = getattr(self.student, 'disability_status', False)

        awarded = rule.points if has_disability else 0
        matched = has_disability

        return DimensionResult(
            criteria_type=rule.criteria_type,
            criteria_display=rule.get_criteria_type_display(),
            raw_value="نعم" if has_disability else "لا",
            awarded_points=awarded,
            max_points=rule.points,
            weight=float(rule.weight),
            weighted_score=awarded * float(rule.weight),
            matched=matched,
            reason="الطالب من ذوي الاحتياجات الخاصة." if matched else "لا ينطبق.",
        )

    def _manual_dimension(self, rule: ScoringRule) -> DimensionResult:
        """بُعد يحتاج تقييم يدوي."""
        return DimensionResult(
            criteria_type=rule.criteria_type,
            criteria_display=rule.get_criteria_type_display(),
            raw_value=None,
            awarded_points=0,
            max_points=rule.points,
            weight=float(rule.weight),
            weighted_score=0,
            matched=False,
            reason="هذا المعيار يحتاج تقييم يدوي من المراجع.",
            is_auto=False,
        )

    # ==============================
    # Utility Methods
    # ==============================
    @staticmethod
    def _safe_decimal(value, default=0) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal(str(default))

    @staticmethod
    def _safe_int(value, default=0) -> int:
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _income_reason(total, cond_min, cond_max, matched):
        if matched:
            return f"إجمالي الدخل: {total} ج.م (ضمن النطاق: {cond_min}-{cond_max})."
        return f"إجمالي الدخل: {total} ج.م (خارج النطاق: {cond_min}-{cond_max})."


def calculate_auto_score(application: AidApplication) -> float:
    """
    دالة مساعدة: حساب الدرجة التلقائية لطلب واحد.
    تُستخدم في الـ signals والـ views.
    """
    engine = ScoringEngine(application)
    result = engine.evaluate()
    return result.total_auto_score


def get_application_scoring_details(application: AidApplication) -> dict:
    """
    دالة مساعدة: إرجاع تفاصيل التقييم الكاملة لطلب واحد.
    تُستخدم في واجهة المراجع.
    """
    engine = ScoringEngine(application)
    result = engine.evaluate()
    return {
        'total_auto_score': result.total_auto_score,
        'max_possible_score': result.max_possible_score,
        'score_percentage': result.score_percentage,
        'dimensions': result.dimensions,
        'has_manual_dimensions': result.has_manual_dimensions,
        'suggestions': engine.get_suggested_scores(),
    }
