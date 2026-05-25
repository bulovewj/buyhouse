import { useState } from 'react'
import { useFetch } from '../hooks/useApi'
import Badge from '../components/Badge'

const SENTIMENT_TABS = [
  { key: '', label: '전체' },
  { key: 'positive', label: '긍정' },
  { key: 'negative', label: '부정' },
  { key: 'neutral', label: '중립' },
]

const SOURCE_TABS = [
  { key: '', label: '전체' },
  { key: 'news', label: '뉴스' },
  { key: 'blog', label: '블로그' },
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

function sourceLabel(type) {
  if (type === 'news') return '뉴스'
  if (type === 'blog') return '블로그'
  return type ?? '-'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return dateStr.split('T')[0]
}

function NewsCard({ item }) {
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
        <Badge text={sentimentLabel(item.sentiment)} variant={sentimentVariant(item.sentiment)} />
      </div>

      {item.summary && (
        <p className="text-gray-400 text-xs leading-relaxed line-clamp-3">{item.summary}</p>
      )}

      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex gap-2">
          <Badge text={sourceLabel(item.source_type)} variant="info" />
          {item.sentiment_score != null && (
            <span className="text-gray-500">점수: {item.sentiment_score.toFixed(2)}</span>
          )}
        </div>
        <span>{formatDate(item.published_at)}</span>
      </div>
    </div>
  )
}

export default function News() {
  const [sentiment, setSentiment] = useState('')
  const [sourceType, setSourceType] = useState('')

  const { data, loading, error } = useFetch('/api/news', {
    sentiment,
    source_type: sourceType,
    page: 1,
    limit: 20,
  })

  const items = data?.items ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">뉴스·반응</h1>
        <p className="text-gray-400 text-sm mt-1">네이버 뉴스·블로그 + Claude AI 감성분석</p>
      </div>

      {/* 감성 필터 */}
      <div className="space-y-2">
        <p className="text-gray-400 text-xs font-medium">감성 필터</p>
        <div className="flex gap-2 flex-wrap">
          {SENTIMENT_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setSentiment(tab.key)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                sentiment === tab.key
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* 출처 필터 */}
      <div className="space-y-2">
        <p className="text-gray-400 text-xs font-medium">출처 필터</p>
        <div className="flex gap-2 flex-wrap">
          {SOURCE_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setSourceType(tab.key)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                sourceType === tab.key
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {loading && <p className="text-gray-400">로딩 중...</p>}
      {error && <p className="text-red-400">데이터를 불러오지 못했습니다: {error}</p>}

      {!loading && !error && (
        <>
          <p className="text-gray-500 text-sm">총 {data?.total ?? 0}건</p>
          {items.length === 0 ? (
            <p className="text-gray-400">뉴스가 없습니다.</p>
          ) : (
            <div className="space-y-4">
              {items.map((item, i) => (
                <NewsCard key={i} item={item} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
