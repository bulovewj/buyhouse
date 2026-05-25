import { useFetch } from '../hooks/useApi'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import Card from '../components/Card'

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

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-gray-700 border border-gray-600 rounded-lg p-3 text-sm">
        <p className="text-white font-semibold">{label}</p>
        <p className="text-blue-400">{formatPrice(payload[0].value)}</p>
      </div>
    )
  }
  return null
}

export default function Market() {
  const { data, loading, error } = useFetch('/api/market-stats')

  const districts = data?.districts ?? []
  const statDate = data?.stat_date ?? ''

  // 수평 막대그래프용: 매매가 기준 정렬
  const chartData = [...districts]
    .sort((a, b) => (a.avg_price ?? 0) - (b.avg_price ?? 0))
    .map((d) => ({
      district: d.district,
      avg_price: d.avg_price ?? 0,
    }))

  // 전세가율 테이블 (매매가 기준 내림차순)
  const jeonseSorted = [...districts].sort((a, b) => (b.avg_price ?? 0) - (a.avg_price ?? 0))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">시세분석</h1>
        {statDate && <p className="text-gray-400 text-sm mt-1">기준일: {statDate}</p>}
      </div>

      {loading && <p className="text-gray-400">로딩 중...</p>}
      {error && <p className="text-red-400">데이터를 불러오지 못했습니다: {error}</p>}

      {!loading && !error && districts.length === 0 && (
        <p className="text-gray-400">데이터가 없습니다.</p>
      )}

      {!loading && !error && districts.length > 0 && (
        <>
          {/* 구별 평균 매매가 수평 막대그래프 */}
          <Card title="구별 평균 매매가">
            <div style={{ height: Math.max(300, chartData.length * 36) }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={chartData}
                  margin={{ top: 0, right: 80, left: 16, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} />
                  <XAxis
                    type="number"
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    tickFormatter={(v) => `${(v / 100_000_000).toFixed(1)}억`}
                    axisLine={{ stroke: '#4b5563' }}
                  />
                  <YAxis
                    type="category"
                    dataKey="district"
                    width={72}
                    tick={{ fill: '#d1d5db', fontSize: 12 }}
                    axisLine={{ stroke: '#4b5563' }}
                  />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(59,130,246,0.1)' }} />
                  <Bar dataKey="avg_price" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* 전세가율 테이블 */}
          <Card title="구별 전세가율">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700 text-gray-400">
                    <th className="text-left py-2 px-3">구</th>
                    <th className="text-right py-2 px-3">평균 매매가</th>
                    <th className="text-right py-2 px-3">평균 전세가</th>
                    <th className="text-right py-2 px-3">전세가율</th>
                  </tr>
                </thead>
                <tbody>
                  {jeonseSorted.map((d) => {
                    const rate = d.jeonse_rate != null ? d.jeonse_rate : null
                    const rateColor =
                      rate == null ? 'text-gray-400'
                      : rate >= 80 ? 'text-red-400'
                      : rate >= 60 ? 'text-yellow-400'
                      : 'text-green-400'
                    return (
                      <tr key={d.district} className="border-b border-gray-700/50 hover:bg-gray-700/20">
                        <td className="py-2 px-3 text-white font-medium">{d.district}</td>
                        <td className="py-2 px-3 text-right text-gray-300">{formatPrice(d.avg_price)}</td>
                        <td className="py-2 px-3 text-right text-gray-300">{formatPrice(d.avg_jeonse_price)}</td>
                        <td className={`py-2 px-3 text-right font-semibold ${rateColor}`}>
                          {rate != null ? `${rate.toFixed(1)}%` : '-'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          {/* 미분양 현황 테이블 */}
          <Card title="미분양 현황">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700 text-gray-400">
                    <th className="text-left py-2 px-3">구</th>
                    <th className="text-right py-2 px-3">미분양 세대</th>
                    <th className="text-right py-2 px-3">거래량</th>
                  </tr>
                </thead>
                <tbody>
                  {[...districts]
                    .sort((a, b) => (b.unsold_count ?? 0) - (a.unsold_count ?? 0))
                    .map((d) => (
                      <tr key={d.district} className="border-b border-gray-700/50 hover:bg-gray-700/20">
                        <td className="py-2 px-3 text-white font-medium">{d.district}</td>
                        <td className="py-2 px-3 text-right">
                          <span className={d.unsold_count > 0 ? 'text-red-400 font-semibold' : 'text-gray-400'}>
                            {d.unsold_count != null ? d.unsold_count.toLocaleString() : '-'}세대
                          </span>
                        </td>
                        <td className="py-2 px-3 text-right text-gray-300">
                          {d.transaction_volume != null ? `${d.transaction_volume.toLocaleString()}건` : '-'}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
