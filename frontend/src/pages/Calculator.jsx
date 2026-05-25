import { useState } from 'react'
import axios from 'axios'
import Card from '../components/Card'

const LOAN_TYPES = [
  { value: '일반', label: '일반 (LTV 70%)' },
  { value: '생애최초', label: '생애최초 (LTV 80%)' },
  { value: '규제지역', label: '규제지역 (LTV 50%)' },
  { value: '임대사업자', label: '임대사업자 (LTV 40%)' },
]

function formatManwon(v) {
  if (v == null || isNaN(v)) return '-'
  const n = Math.round(v)
  const uk = Math.floor(n / 10000)
  const rest = n % 10000
  if (uk > 0 && rest > 0) return `${uk}억 ${rest.toLocaleString()}만원`
  if (uk > 0) return `${uk}억`
  return `${rest.toLocaleString()}만원`
}

function ResultRow({ label, value, highlight = false, sub, subColor = 'text-gray-500' }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-700 last:border-0">
      <div>
        <p className={`text-sm font-medium ${highlight ? 'text-blue-300' : 'text-gray-300'}`}>{label}</p>
        {sub && <p className={`text-xs mt-0.5 ${subColor}`}>{sub}</p>}
      </div>
      <p className={`font-bold ${highlight ? 'text-blue-400 text-lg' : 'text-white'}`}>{value}</p>
    </div>
  )
}

function InputField({ label, value, onChange, placeholder, type = 'number', min, max, step }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-gray-400 text-sm font-medium">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        min={min}
        max={max}
        step={step}
        className="bg-gray-700 text-white rounded-lg px-3 py-2.5 text-sm border border-gray-600 focus:outline-none focus:border-blue-500 placeholder-gray-500"
        required
      />
    </div>
  )
}

export default function Calculator() {
  const [housePrice, setHousePrice] = useState('')
  const [ownFund, setOwnFund] = useState('')
  const [annualIncome, setAnnualIncome] = useState('')
  const [loanYears, setLoanYears] = useState('30')
  const [interestRate, setInterestRate] = useState('3.5')
  const [loanType, setLoanType] = useState('일반')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function calculate(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await axios.post('/api/calculator/calculate', {
        house_price: parseInt(housePrice),
        own_fund: parseInt(ownFund),
        annual_income: parseInt(annualIncome),
        loan_years: parseInt(loanYears),
        interest_rate: parseFloat(interestRate),
        loan_type: loanType,
      })
      setResult(res.data)
    } catch (e) {
      const detail = e.response?.data?.detail
      if (Array.isArray(detail)) {
        setError(detail.map((d) => d.msg).join(', '))
      } else {
        setError(detail ?? e.message)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-white">대출계산기</h1>
        <p className="text-gray-400 text-sm mt-1">LTV·DSR 기준 대출 가능 여부를 확인하세요</p>
      </div>

      <Card title="조건 입력">
        <form onSubmit={calculate} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <InputField
              label="주택 가격 (만원)"
              value={housePrice}
              onChange={setHousePrice}
              placeholder="예: 50000"
              min="0"
            />
            <InputField
              label="본인 자금 (만원)"
              value={ownFund}
              onChange={setOwnFund}
              placeholder="예: 15000"
              min="0"
            />
            <InputField
              label="연 소득 (만원)"
              value={annualIncome}
              onChange={setAnnualIncome}
              placeholder="예: 5000"
              min="0"
            />
            <div className="flex flex-col gap-1.5">
              <label className="text-gray-400 text-sm font-medium">대출 기간 (년)</label>
              <select
                value={loanYears}
                onChange={(e) => setLoanYears(e.target.value)}
                className="bg-gray-700 text-white rounded-lg px-3 py-2.5 text-sm border border-gray-600 focus:outline-none focus:border-blue-500"
              >
                {[10, 15, 20, 25, 30, 35, 40].map((y) => (
                  <option key={y} value={y}>{y}년</option>
                ))}
              </select>
            </div>
            <InputField
              label="연 금리 (%)"
              value={interestRate}
              onChange={setInterestRate}
              placeholder="예: 3.5"
              min="0.1"
              max="20"
              step="0.1"
            />
            <div className="flex flex-col gap-1.5">
              <label className="text-gray-400 text-sm font-medium">대출 유형</label>
              <select
                value={loanType}
                onChange={(e) => setLoanType(e.target.value)}
                className="bg-gray-700 text-white rounded-lg px-3 py-2.5 text-sm border border-gray-600 focus:outline-none focus:border-blue-500"
              >
                {LOAN_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg px-4 py-3 font-semibold transition-colors"
          >
            {loading ? '계산 중...' : '계산하기'}
          </button>
        </form>
      </Card>

      {result && (
        <>
          <Card title="계산 결과">
            <p className="text-xs text-gray-500 mb-3">{result.loan_type_label}</p>
            <ResultRow
              label="필요 대출액"
              value={formatManwon(result.loan_needed)}
              highlight
            />
            <ResultRow
              label={`LTV 한도 (${Math.round(result.ltv_rate * 100)}%)`}
              value={formatManwon(result.ltv_limit)}
              sub={result.ltv_ok ? '✅ LTV 범위 내' : '⚠️ LTV 한도 초과 — 자금 보완 필요'}
              subColor={result.ltv_ok ? 'text-green-400' : 'text-yellow-400'}
            />
            <ResultRow
              label="DSR 월 한도 (연소득 40% ÷ 12)"
              value={formatManwon(result.dsr_monthly_limit)}
              sub={result.dsr_ok ? '✅ DSR 범위 내' : '⚠️ DSR 한도 초과 — 소득 또는 기간 조정 필요'}
              subColor={result.dsr_ok ? 'text-green-400' : 'text-yellow-400'}
            />
            <ResultRow
              label={`월 예상 상환액 (${result.loan_years}년, ${result.interest_rate}%)`}
              value={formatManwon(result.monthly_payment)}
              highlight
            />
            <ResultRow
              label={`스트레스 DSR 월 상환액 (${(result.interest_rate + 1.5).toFixed(1)}%)`}
              value={formatManwon(result.stress_monthly_payment)}
              sub={result.stress_dsr_ok ? '✅ 스트레스 DSR 통과' : '⚠️ 스트레스 DSR 초과 (2024.09~ 적용)'}
              subColor={result.stress_dsr_ok ? 'text-green-400' : 'text-yellow-400'}
            />
            <ResultRow label="총 상환액" value={formatManwon(result.total_repayment)} />
            <ResultRow
              label="총 이자액"
              value={formatManwon(result.total_interest)}
              sub={`원금의 ${result.loan_needed > 0 ? Math.round((result.total_interest / result.loan_needed) * 100) : 0}%`}
            />
          </Card>

          {/* 종합 판정 */}
          <div className={`rounded-xl p-4 text-sm font-medium border ${
            result.feasible
              ? 'bg-green-900/40 text-green-300 border-green-700'
              : 'bg-red-900/40 text-red-300 border-red-700'
          }`}>
            {result.feasible
              ? '✅ LTV·DSR 기준 내에서 대출이 가능한 것으로 보입니다.'
              : [
                  !result.ltv_ok && 'LTV 초과: 자금을 더 마련하거나 저렴한 매물을 검토하세요.',
                  !result.dsr_ok && 'DSR 초과: 대출 기간을 늘리거나 소득 증빙을 보완하세요.',
                ].filter(Boolean).map((msg, i) => <p key={i}>⚠️ {msg}</p>)
            }
          </div>
        </>
      )}

      {/* 주의 문구 */}
      <div className="bg-yellow-900/30 border border-yellow-700 rounded-xl p-4 text-yellow-300 text-sm">
        <p className="font-semibold mb-1">⚠️ 주의사항</p>
        <ul className="space-y-0.5 text-yellow-400 text-xs list-disc list-inside">
          <li>본 계산기는 참고용이며 법적 효력이 없습니다.</li>
          <li>실제 대출 한도·금리는 금융기관과 상담하세요.</li>
          <li>2024.09~ 스트레스 DSR 2단계(가산 1.5%p) 기준으로 참고 수치를 함께 표시합니다.</li>
          <li>규제지역 지정 여부 등 세부 조건은 금융기관에 확인하세요.</li>
        </ul>
      </div>
    </div>
  )
}
