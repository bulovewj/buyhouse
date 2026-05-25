from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["calculator"])

# 대출 유형별 LTV 한도 (2024년 기준 부산 비규제지역 기준)
LTV_RULES: dict[str, dict] = {
    "일반": {"ltv": 0.70, "label": "일반 주택담보대출 (비규제, LTV 70%)"},
    "생애최초": {"ltv": 0.80, "label": "생애최초 주택구입 (비규제, LTV 80%)"},
    "규제지역": {"ltv": 0.50, "label": "규제지역 (투기과열·조정대상, LTV 50%)"},
    "임대사업자": {"ltv": 0.40, "label": "임대사업자 (LTV 40%)"},
}

DSR_LIMIT = 0.40   # 총부채원리금상환비율 40%
STRESS_DSR_BUFFER = 0.015  # 스트레스 DSR 가산금리 1.5%p (2단계, 2024.09~)


class CalcRequest(BaseModel):
    house_price: int = Field(..., gt=0, description="주택 가격 (만원)")
    own_fund: int = Field(..., ge=0, description="본인 자금 (만원)")
    annual_income: int = Field(..., gt=0, description="연 소득 (만원)")
    loan_years: int = Field(30, ge=1, le=50, description="대출 기간 (년)")
    interest_rate: float = Field(3.5, ge=0.1, le=20.0, description="연 금리 (%)")
    loan_type: str = Field("일반", description="대출 유형: 일반|생애최초|규제지역|임대사업자")


class CalcResult(BaseModel):
    # 입력 요약
    house_price: int
    own_fund: int
    annual_income: int
    loan_years: int
    interest_rate: float
    loan_type: str
    loan_type_label: str

    # 핵심 수치 (만원)
    loan_needed: int
    ltv_limit: int
    ltv_rate: float
    ltv_ok: bool

    dsr_monthly_limit: int
    dsr_ok: bool
    monthly_payment: int

    total_repayment: int
    total_interest: int

    # 스트레스 DSR 적용 월 상환액 (참고용)
    stress_monthly_payment: int
    stress_dsr_ok: bool

    feasible: bool


@router.post("/calculator/calculate", response_model=CalcResult)
async def calculate(body: CalcRequest):
    rule = LTV_RULES.get(body.loan_type, LTV_RULES["일반"])
    ltv_rate = rule["ltv"]

    hp = body.house_price
    of = body.own_fund
    ai = body.annual_income
    years = body.loan_years
    rate = body.interest_rate / 100  # 연 이율 (소수)

    # 필요 대출액
    loan_needed = max(0, hp - of)

    # LTV 한도
    ltv_limit = int(hp * ltv_rate)
    ltv_ok = loan_needed <= ltv_limit

    # DSR 월 한도 (연소득 × 40% ÷ 12)
    dsr_monthly_limit = int(ai * DSR_LIMIT / 12)

    # 월 원리금균등상환액 계산
    monthly_payment = _calc_monthly(loan_needed, rate, years)
    dsr_ok = monthly_payment <= dsr_monthly_limit

    # 스트레스 DSR: 금리 + 가산 1.5%p 적용
    stress_rate = rate + STRESS_DSR_BUFFER
    stress_monthly_payment = _calc_monthly(loan_needed, stress_rate, years)
    stress_dsr_ok = stress_monthly_payment <= dsr_monthly_limit

    n = years * 12
    total_repayment = monthly_payment * n
    total_interest = max(0, total_repayment - loan_needed)

    return CalcResult(
        house_price=hp,
        own_fund=of,
        annual_income=ai,
        loan_years=years,
        interest_rate=body.interest_rate,
        loan_type=body.loan_type,
        loan_type_label=rule["label"],
        loan_needed=loan_needed,
        ltv_limit=ltv_limit,
        ltv_rate=ltv_rate,
        ltv_ok=ltv_ok,
        dsr_monthly_limit=dsr_monthly_limit,
        dsr_ok=dsr_ok,
        monthly_payment=monthly_payment,
        total_repayment=total_repayment,
        total_interest=total_interest,
        stress_monthly_payment=stress_monthly_payment,
        stress_dsr_ok=stress_dsr_ok,
        feasible=ltv_ok and dsr_ok,
    )


def _calc_monthly(principal_manwon: int, annual_rate: float, years: int) -> int:
    """원리금균등상환 월 납부액 (만원 단위 반환)."""
    if principal_manwon <= 0:
        return 0
    r = annual_rate / 12
    n = years * 12
    if r == 0:
        return int(principal_manwon / n)
    payment = principal_manwon * r / (1 - (1 + r) ** (-n))
    return int(payment)
