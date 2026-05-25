import { useFetch } from '../hooks/useApi'
import Badge from '../components/Badge'
import Card from '../components/Card'

// 정적 정책 현황 카드 3개
const POLICY_CARDS = [
  {
    title: 'DSR 현황',
    icon: '📊',
    description:
      '총부채원리금상환비율(DSR) 규제 적용 중. 은행권 40%, 2금융권 50% 한도. 개인별 연소득 대비 전체 금융부채 원리금 비율이 기준 이하여야 대출 가능.',
    link: 'https://www.fss.or.kr',
    linkLabel: '금융감독원 바로가기',
  },
  {
    title: 'LTV 규제',
    icon: '🏦',
    description:
      '주택담보인정비율(LTV). 규제지역 50%, 비규제지역 70% 적용. 실수요자 우대 조건 충족 시 최대 80%까지 가능. 부산 일부 지역은 조정대상지역에서 해제.',
    link: 'https://www.molit.go.kr',
    linkLabel: '국토교통부 바로가기',
  },
  {
    title: '특별공급 제도',
    icon: '🎯',
    description:
      '신혼부부, 생애최초, 다자녀, 노부모부양, 기관추천 등 특별공급 유형별 자격 요건 상이. 소득·자산 기준 초과 시 일반공급으로 전환. 무주택 기간 및 청약통장 가입기간 필수.',
    link: 'https://www.applyhome.co.kr',
    linkLabel: '청약홈 바로가기',
  },
]

function sentimentVariant(sentiment) {
  if (sentiment === 'positive') return 'success'
  if (sentiment === 'negative') return 'danger'
  return 'default'
}

function sentimentLabel(sentiment) {
  if (sentiment === 'positive') return '긍정'
  if (sentiment === 'negative') return '부정'
  if (sentiment === 'neutral') return '중립'
  return sentiment ?? '-'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return dateStr.split('T')[0]
}

function PolicyNewsCard({ item }) {
  return (
    <div className="bg-gray-800 rounded-xl shadow-lg p-5 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <a
          href={item.source_url || '#'}
          target="_blank"
          rel="noopener noreferrer"
          className="text-white font-semibold text-sm leading-snug hover:text-blue-400 transition-colors flex-1"
        >
          {item.title}
        </a>
        {item.sentiment && (
          <Badge text={sentimentLabel(item.sentiment)} variant={sentimentVariant(item.sentiment)} />
        )}
      </div>
      {item.summary && (
        <p className="text-gray-400 text-xs leading-relaxed line-clamp-3">{item.summary}</p>
      )}
      <p className="text-gray-500 text-xs">{formatDate(item.published_at)}</p>
    </div>
  )
}

export default function Policy() {
  const { data, loading, error } = useFetch('/api/policy-news', { page: 1, limit: 20 })
  const items = data?.items ?? []

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">정책뉴스</h1>
        <p className="text-gray-400 text-sm mt-1">부동산 정책·규제 정보 및 관련 뉴스</p>
      </div>

      {/* 주요 정책 현황 카드 3개 (하드코딩) */}
      <div>
        <h2 className="text-lg font-bold text-white mb-4">주요 정책 현황</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {POLICY_CARDS.map((card) => (
            <div key={card.title} className="bg-gray-800 rounded-xl shadow-lg p-5 flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{card.icon}</span>
                <h3 className="text-white font-bold text-base">{card.title}</h3>
              </div>
              <p className="text-gray-400 text-sm leading-relaxed flex-1">{card.description}</p>
              <a
                href={card.link}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-4 py-2 text-sm font-medium text-center transition-colors"
              >
                {card.linkLabel}
              </a>
            </div>
          ))}
        </div>
      </div>

      {/* 정책 관련 뉴스 */}
      <div>
        <h2 className="text-lg font-bold text-white mb-4">정책 관련 뉴스</h2>
        {loading && <p className="text-gray-400">로딩 중...</p>}
        {error && <p className="text-red-400">데이터를 불러오지 못했습니다: {error}</p>}
        {!loading && !error && (
          <>
            <p className="text-gray-500 text-sm mb-4">총 {data?.total ?? 0}건</p>
            {items.length === 0 ? (
              <p className="text-gray-400">뉴스가 없습니다.</p>
            ) : (
              <div className="space-y-4">
                {items.map((item, i) => (
                  <PolicyNewsCard key={i} item={item} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
