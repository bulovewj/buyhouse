import { useFetch } from '../hooks/useApi'
import Card from '../components/Card'
import Badge from '../components/Badge'

const SENTIMENT_COLOR = { positive: 'text-green-400', negative: 'text-red-400', neutral: 'text-gray-400' }
const SENTIMENT_LABEL = { positive: '긍정', negative: '부정', neutral: '중립' }

// 가격 포맷: 원(won) 단위 입력 → "X억 Y,000만원"
function formatPrice(won) {
  if (won == null) return '-'
  const manwon = Math.round(won / 10000)
  const uk = Math.floor(manwon / 10000)
  const rest = manwon % 10000
  if (uk > 0 && rest > 0) return `${uk}억 ${rest.toLocaleString()}만원`
  if (uk > 0) return `${uk}억`
  return `${rest.toLocaleString()}만원`
}

function typeLabel(type) {
  const map = {
    subscription: '청약',
    jjupjjup: '줍줍',
    happy_house: '행복주택',
    public_rental: '공공임대',
  }
  return map[type] ?? type
}

function typeVariant(type) {
  const map = {
    subscription: 'info',
    jjupjjup: 'warning',
    happy_house: 'success',
    public_rental: 'default',
  }
  return map[type] ?? 'default'
}

function statusVariant(status) {
  if (status === '접수중') return 'success'
  if (status === '마감') return 'danger'
  if (status === '예정') return 'info'
  return 'default'
}

function SummaryCard({ label, value, sub, color = 'text-blue-400' }) {
  return (
    <div className="bg-gray-800 rounded-xl shadow-lg p-6 flex flex-col gap-2">
      <p className="text-gray-400 text-sm">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-gray-500 text-xs">{sub}</p>}
    </div>
  )
}

export default function Dashboard() {
  const { data: subData, loading: subLoading, error: subError } = useFetch('/api/subscriptions', { page: 1, limit: 5 })
  const { data: marketData, loading: marketLoading, error: marketError } = useFetch('/api/market-stats')
  const { data: newsData, loading: newsLoading } = useFetch('/api/news', { limit: 4 })

  const totalSubs = subData?.total ?? '-'
  const recentItems = subData?.items ?? []

  // 평균 매매가 (전 구 평균)
  const districts = marketData?.districts ?? []
  const avgPrice = districts.length
    ? Math.round(districts.reduce((sum, d) => sum + (d.avg_price ?? 0), 0) / districts.length)
    : null
  const totalUnsold = districts.reduce((sum, d) => sum + (d.unsold_count ?? 0), 0)
  const totalVolume = districts.reduce((sum, d) => sum + (d.transaction_volume ?? 0), 0)

  const statDate = marketData?.stat_date ?? ''

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">대시보드</h1>
        {statDate && <p className="text-gray-500 text-sm mt-1">기준일: {statDate}</p>}
      </div>

      {/* 요약 카드 4개 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          label="청약·공고 수"
          value={subLoading ? '...' : totalSubs}
          sub="현재 공고 중"
          color="text-blue-400"
        />
        <SummaryCard
          label="부산 평균 매매가"
          value={marketLoading ? '...' : avgPrice ? formatPrice(avgPrice) : '-'}
          sub="전 구 평균"
          color="text-emerald-400"
        />
        <SummaryCard
          label="총 거래량"
          value={marketLoading ? '...' : totalVolume ? `${totalVolume.toLocaleString()}건` : '-'}
          sub={statDate ? `${statDate} 기준` : ''}
          color="text-yellow-400"
        />
        <SummaryCard
          label="총 미분양"
          value={marketLoading ? '...' : totalUnsold ? `${totalUnsold.toLocaleString()}세대` : '-'}
          sub="전 구 합계"
          color="text-red-400"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 최근 청약 공고 */}
        <Card title="최근 청약·공고">
          {subLoading && <p className="text-gray-400">로딩 중...</p>}
          {subError && <p className="text-red-400 text-sm">데이터를 불러오지 못했습니다.</p>}
          {!subLoading && !subError && recentItems.length === 0 && (
            <p className="text-gray-400 text-sm">공고가 없습니다.</p>
          )}
          <ul className="space-y-3">
            {recentItems.map((item) => (
              <li key={item.id} className="flex items-start justify-between gap-3 border-b border-gray-700 pb-3 last:border-0 last:pb-0">
                <div className="flex-1 min-w-0">
                  <p className="text-white text-sm font-medium truncate">{item.title}</p>
                  <p className="text-gray-400 text-xs mt-0.5">{item.location}</p>
                  <p className="text-gray-500 text-xs mt-0.5">
                    {item.application_start} ~ {item.application_end}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-1 shrink-0">
                  <Badge text={typeLabel(item.type)} variant={typeVariant(item.type)} />
                  <Badge text={item.status} variant={statusVariant(item.status)} />
                </div>
              </li>
            ))}
          </ul>
        </Card>

        {/* AI 분석 요약 */}
        <Card title="🤖 AI 뉴스 분석">
          {newsLoading && <p className="text-gray-400 text-sm">로딩 중...</p>}
          {!newsLoading && (newsData?.items ?? []).length === 0 && (
            <p className="text-gray-500 text-sm">분석된 뉴스가 없습니다.</p>
          )}
          <ul className="space-y-4">
            {(newsData?.items ?? []).map((item, i) => (
              <li key={i} className="border-b border-gray-700 pb-4 last:border-0 last:pb-0">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-white text-sm font-medium hover:text-blue-400 line-clamp-2 flex-1"
                  >
                    {item.title}
                  </a>
                  {item.sentiment && (
                    <span className={`text-xs font-medium shrink-0 ${SENTIMENT_COLOR[item.sentiment] ?? 'text-gray-400'}`}>
                      {SENTIMENT_LABEL[item.sentiment] ?? item.sentiment}
                    </span>
                  )}
                </div>
                {item.summary && (
                  <p className="text-gray-400 text-xs leading-relaxed">{item.summary}</p>
                )}
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  )
}
