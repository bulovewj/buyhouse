import { useState, useEffect } from 'react'
import axios from 'axios'
import { useFetch } from '../hooks/useApi'
import Card from '../components/Card'

function Toggle({ checked, onChange, disabled }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
        checked ? 'bg-blue-600' : 'bg-gray-600'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  )
}

export default function Settings() {
  const { data: initData, loading, error: fetchError } = useFetch('/api/settings')

  const [form, setForm] = useState({
    kakao_enabled: false,
    email_enabled: false,
    email_address: '',
    notify_subscription: true,
    notify_jjupjjup: true,
    notify_happy_house: true,
    notify_public_rental: true,
    notify_policy: true,
  })

  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [saveError, setSaveError] = useState('')

  // 서버에서 받아온 초기 데이터로 form 초기화
  useEffect(() => {
    if (initData) {
      setForm({
        kakao_enabled: initData.kakao_enabled ?? false,
        email_enabled: initData.email_enabled ?? false,
        email_address: initData.email_address ?? '',
        notify_subscription: initData.notify_subscription ?? true,
        notify_jjupjjup: initData.notify_jjupjjup ?? true,
        notify_happy_house: initData.notify_happy_house ?? true,
        notify_public_rental: initData.notify_public_rental ?? true,
        notify_policy: initData.notify_policy ?? true,
      })
    }
  }, [initData])

  async function updateField(field, value) {
    const newForm = { ...form, [field]: value }
    setForm(newForm)
    await save(newForm)
  }

  async function save(data = form) {
    setSaving(true)
    setSaveMsg('')
    setSaveError('')
    try {
      await axios.put('/api/settings', data)
      setSaveMsg('저장됨 ✓')
      setTimeout(() => setSaveMsg(''), 2000)
    } catch (e) {
      setSaveError('저장 실패: ' + (e.response?.data?.detail ?? e.message))
    } finally {
      setSaving(false)
    }
  }

  function handleEmailSubmit(e) {
    e.preventDefault()
    save()
  }

  if (loading) return <p className="text-gray-400">로딩 중...</p>
  if (fetchError) return <p className="text-red-400">설정을 불러오지 못했습니다: {fetchError}</p>

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">설정</h1>
          <p className="text-gray-400 text-sm mt-1">알림 채널 및 수신 항목을 설정하세요</p>
        </div>
        {saving && <p className="text-gray-400 text-sm">저장 중...</p>}
        {saveMsg && <p className="text-green-400 text-sm font-medium">{saveMsg}</p>}
        {saveError && <p className="text-red-400 text-sm">{saveError}</p>}
      </div>

      {/* 알림 채널 */}
      <Card title="알림 채널">
        <div className="space-y-5">
          {/* 카카오톡 */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white font-medium text-sm">카카오톡 알림</p>
              <p className="text-gray-500 text-xs mt-0.5">신규 공고 발생 시 카톡(나에게 보내기)으로 알림</p>
            </div>
            <Toggle
              checked={form.kakao_enabled}
              onChange={(val) => updateField('kakao_enabled', val)}
              disabled={saving}
            />
          </div>

          <div className="border-t border-gray-700" />

          {/* 이메일 */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-medium text-sm">이메일 알림</p>
                <p className="text-gray-500 text-xs mt-0.5">Gmail SMTP 기반 이메일 수신</p>
              </div>
              <Toggle
                checked={form.email_enabled}
                onChange={(val) => updateField('email_enabled', val)}
                disabled={saving}
              />
            </div>

            {form.email_enabled && (
              <form onSubmit={handleEmailSubmit} className="flex gap-2">
                <input
                  type="email"
                  value={form.email_address}
                  onChange={(e) => setForm({ ...form, email_address: e.target.value })}
                  placeholder="수신 이메일 주소"
                  className="flex-1 bg-gray-700 text-white rounded-lg px-3 py-2 text-sm border border-gray-600 focus:outline-none focus:border-blue-500 placeholder-gray-500"
                />
                <button
                  type="submit"
                  disabled={saving}
                  className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                >
                  저장
                </button>
              </form>
            )}
          </div>
        </div>
      </Card>

      {/* 알림 항목 */}
      <Card title="알림 항목">
        <div className="space-y-4">
          {[
            { field: 'notify_subscription', label: '청약 공고', desc: '일반 청약 모집공고 알림' },
            { field: 'notify_jjupjjup', label: '줍줍 (무순위)', desc: '무순위 청약 긴급 공고 알림 (6시간 주기)' },
            { field: 'notify_happy_house', label: '행복주택', desc: '행복주택 모집공고 알림' },
            { field: 'notify_public_rental', label: '공공임대', desc: '공공임대 모집공고 알림' },
            { field: 'notify_policy', label: '정책 뉴스', desc: '부동산 정책·규제 관련 뉴스 알림' },
          ].map(({ field, label, desc }) => (
            <div key={field} className="flex items-center justify-between">
              <div>
                <p className="text-white text-sm font-medium">{label}</p>
                <p className="text-gray-500 text-xs mt-0.5">{desc}</p>
              </div>
              <Toggle
                checked={form[field]}
                onChange={(val) => updateField(field, val)}
                disabled={saving}
              />
            </div>
          ))}
        </div>
      </Card>

      {/* 데이터 갱신 안내 */}
      <div className="bg-gray-800 rounded-xl p-4 text-xs text-gray-400 space-y-1">
        <p className="font-semibold text-gray-300">갱신 주기 안내</p>
        <p>• 전체 데이터: 매일 00:00 KST 자동 갱신</p>
        <p>• 줍줍(무순위) 긴급 공고: 매 6시간마다 체크</p>
      </div>
    </div>
  )
}
