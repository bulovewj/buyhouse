import { useState } from 'react'
import { useFetch } from '../hooks/useApi'

const DISTRICTS = [
  '', '중구', '서구', '동구', '영도구', '부산진구', '동래구', '남구',
  '북구', '해운대구', '사하구', '금정구', '강서구', '연제구', '수영구',
  '사상구', '기장군',
]

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

export default function Transactions() {
  const [district, setDistrict] = useState('')
  const [dong, setDong] = useState('')
  const [page, setPage] = useState(1)
  const LIMIT = 20

  const { data, loading, error } = useFetch('/api/transactions', {
    district,
    dong,
    page,
    limit: LIMIT,
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / LIMIT)

  function handleSearch(e) {
    e.preventDefault()
    setPage(1)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">실거래가</h1>
        <p className="text-gray-400 text-sm mt-1">부산 아파트·빌라 실거래가 (국토부)</p>
      </div>

      {/* 검색 필터 */}
      <form onSubmit={handleSearch} className="bg-gray-800 rounded-xl p-4 flex flex-wrap gap-3 items-end">
        <div className="flex flex-col gap-1">
          <label className="text-gray-400 text-xs">구 선택</label>
          <select
            value={district}
            onChange={(e) => { setDistrict(e.target.value); setPage(1) }}
            className="bg-gray-700 text-white rounded-lg px-3 py-2 text-sm border border-gray-600 focus:outline-none focus:border-blue-500"
          >
            {DISTRICTS.map((d) => (
              <option key={d} value={d}>{d || '전체'}</option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-gray-400 text-xs">동 입력</label>
          <input
            type="text"
            value={dong}
            onChange={(e) => { setDong(e.target.value); setPage(1) }}
            placeholder="예: 해운대동"
            className="bg-gray-700 text-white rounded-lg px-3 py-2 text-sm border border-gray-600 focus:outline-none focus:border-blue-500 placeholder-gray-500"
          />
        </div>
        <button
          type="submit"
          className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        >
          검색
        </button>
      </form>

      {loading && <p className="text-gray-400">로딩 중...</p>}
      {error && <p className="text-red-400">데이터를 불러오지 못했습니다: {error}</p>}

      {!loading && !error && (
        <>
          <p className="text-gray-500 text-sm">총 {total.toLocaleString()}건</p>

          {/* 테이블 (PC) */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700 text-gray-400">
                  <th className="text-left py-3 px-4">단지명</th>
                  <th className="text-left py-3 px-4">구/동</th>
                  <th className="text-left py-3 px-4">거래일</th>
                  <th className="text-right py-3 px-4">면적(m²)</th>
                  <th className="text-right py-3 px-4">층</th>
                  <th className="text-right py-3 px-4">거래가</th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-gray-400">
                      거래 내역이 없습니다.
                    </td>
                  </tr>
                ) : (
                  items.map((item, i) => (
                    <tr
                      key={i}
                      className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors"
                    >
                      <td className="py-3 px-4 text-white font-medium">{item.building_name || '-'}</td>
                      <td className="py-3 px-4 text-gray-300">{item.district} {item.dong}</td>
                      <td className="py-3 px-4 text-gray-300">{item.deal_date || '-'}</td>
                      <td className="py-3 px-4 text-right text-gray-300">{item.area_m2 != null ? item.area_m2.toFixed(1) : '-'}</td>
                      <td className="py-3 px-4 text-right text-gray-300">{item.floor != null ? `${item.floor}층` : '-'}</td>
                      <td className="py-3 px-4 text-right text-blue-400 font-semibold">{formatPrice(item.price_won)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* 카드 리스트 (모바일) */}
          <div className="md:hidden space-y-3">
            {items.length === 0 ? (
              <p className="text-gray-400 text-center py-8">거래 내역이 없습니다.</p>
            ) : (
              items.map((item, i) => (
                <div key={i} className="bg-gray-800 rounded-xl p-4 space-y-2">
                  <div className="flex justify-between items-start">
                    <p className="text-white font-semibold text-sm">{item.building_name || '-'}</p>
                    <p className="text-blue-400 font-bold text-sm">{formatPrice(item.price_won)}</p>
                  </div>
                  <p className="text-gray-400 text-xs">{item.district} {item.dong}</p>
                  <div className="flex gap-4 text-xs text-gray-500">
                    <span>{item.deal_date}</span>
                    <span>{item.area_m2 != null ? `${item.area_m2.toFixed(1)}m²` : ''}</span>
                    <span>{item.floor != null ? `${item.floor}층` : ''}</span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* 페이지네이션 */}
          {totalPages > 1 && (
            <div className="flex justify-center gap-2 flex-wrap">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 rounded-lg bg-gray-700 text-gray-300 text-sm disabled:opacity-40 hover:bg-gray-600 transition-colors"
              >
                이전
              </button>
              {Array.from({ length: Math.min(totalPages, 10) }, (_, i) => {
                const pageNum = i + 1
                return (
                  <button
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                      page === pageNum
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {pageNum}
                  </button>
                )
              })}
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1.5 rounded-lg bg-gray-700 text-gray-300 text-sm disabled:opacity-40 hover:bg-gray-600 transition-colors"
              >
                다음
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
