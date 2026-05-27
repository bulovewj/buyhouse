import { useState } from 'react'
import { useFetch } from '../hooks/useApi'
import Badge from '../components/Badge'

const TABS = [
  { key: '', label: '전체' },
  { key: '청약', label: '청약' },
  { key: '줍줍', label: '줍줍' },
  { key: '행복주택', label: '행복주택' },
  { key: '공공임대', label: '공공임대' },
]

function typeLabel(type) {
  return type ?? '-'
}

function typeVariant(type) {
  const map = {
    '청약': 'info',
    '줍줍': 'warning',
    '행복주택': 'success',
    '공공임대': 'default',
  }
  return map[type] ?? 'default'
}

function statusVariant(status) {
  if (status === '접수중') return 'success'
  if (status === '마감') return 'danger'
  if (status === '예정') return 'info'
  return 'default'
}

// D-day 계산
function calcDday(endDateStr) {
  if (!endDateStr) return null
  const end = new Date(endDateStr)
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  end.setHours(0, 0, 0, 0)
  const diff = Math.ceil((end - now) / (1000 * 60 * 60 * 24))
  return diff
}

function DdayBadge({ endDate }) {
  const diff = calcDday(endDate)
  if (diff == null) return null
  if (diff < 0) return <Badge text="마감" variant="danger" />
  if (diff === 0) return <Badge text="D-Day" variant="danger" />
  if (diff <= 3) return <Badge text={`D-${diff} 마감임박`} variant="warning" />
  return <Badge text={`D-${diff}`} variant="default" />
}

function SubscriptionCard({ item }) {
  const dday = calcDday(item.application_end)
  const isUrgent = dday != null && dday >= 0 && dday <= 3

  return (
    <div className={`bg-gray-800 rounded-xl shadow-lg p-5 flex flex-col gap-3 border ${isUrgent ? 'border-yellow-600' : 'border-transparent'}`}>
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-white font-semibold text-sm leading-snug flex-1">{item.title}</h3>
        <Badge text={typeLabel(item.type)} variant={typeVariant(item.type)} />
      </div>

      <p className="text-gray-400 text-xs">{item.location}</p>

      <div className="flex items-center gap-2 flex-wrap">
        <Badge text={item.status} variant={statusVariant(item.status)} />
        <DdayBadge endDate={item.application_end} />
        {isUrgent && <Badge text="마감임박" variant="warning" />}
      </div>

      <div className="border-t border-gray-700 pt-3 grid grid-cols-2 gap-2 text-xs">
        <div>
          <p className="text-gray-500">공급세대</p>
          <p className="text-white font-medium">{item.supply_count != null ? `${item.supply_count.toLocaleString()}세대` : '-'}</p>
        </div>
        <div>
          <p className="text-gray-500">신청 기간</p>
          <p className="text-white font-medium">
            {item.application_start} ~<br />{item.application_end}
          </p>
        </div>
      </div>
    </div>
  )
}

export default function Subscriptions() {
  const [activeTab, setActiveTab] = useState('')

  const { data, loading, error } = useFetch('/api/subscriptions', {
    type: activeTab,
    page: 1,
    limit: 20,
  })

  const items = data?.items ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">청약·공고</h1>
        <p className="text-gray-400 text-sm mt-1">청약, 줍줍, 행복주택, 공공임대 모집공고</p>
      </div>

      {/* 탭 필터 */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`shrink-0 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading && <p className="text-gray-400">로딩 중...</p>}
      {error && <p className="text-red-400">데이터를 불러오지 못했습니다: {error}</p>}

      {!loading && !error && (
        <>
          <p className="text-gray-500 text-sm">총 {data?.total ?? 0}건</p>
          {items.length === 0 ? (
            <p className="text-gray-400">해당 유형의 공고가 없습니다.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {items.map((item) => (
                <SubscriptionCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
