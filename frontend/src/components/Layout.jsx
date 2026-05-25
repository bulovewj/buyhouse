import { NavLink, useLocation } from 'react-router-dom'

const navItems = [
  { path: '/', label: '대시보드', icon: '📊' },
  { path: '/subscriptions', label: '청약·공고', icon: '📋' },
  { path: '/transactions', label: '실거래가', icon: '💰' },
  { path: '/market', label: '시세분석', icon: '📈' },
  { path: '/news', label: '뉴스·반응', icon: '📰' },
  { path: '/policy', label: '정책뉴스', icon: '🏛️' },
  { path: '/calculator', label: '대출계산기', icon: '🧮' },
  { path: '/settings', label: '설정', icon: '⚙️' },
]

function SidebarLink({ path, label, icon }) {
  return (
    <NavLink
      to={path}
      end={path === '/'}
      className={({ isActive }) =>
        `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
          isActive
            ? 'bg-blue-600 text-white'
            : 'text-gray-400 hover:bg-gray-700 hover:text-white'
        }`
      }
    >
      <span className="text-base">{icon}</span>
      {label}
    </NavLink>
  )
}

function BottomTabLink({ path, label, icon }) {
  return (
    <NavLink
      to={path}
      end={path === '/'}
      className={({ isActive }) =>
        `flex flex-col items-center gap-0.5 px-2 py-1 text-xs transition-colors ${
          isActive ? 'text-blue-400' : 'text-gray-500'
        }`
      }
    >
      <span className="text-xl">{icon}</span>
      <span className="truncate max-w-[56px] text-center">{label}</span>
    </NavLink>
  )
}

export default function Layout({ children }) {
  // 하단 탭은 주요 5개 항목만 표시 (모바일 공간 제한)
  const mobileNavItems = [
    navItems[0],
    navItems[1],
    navItems[2],
    navItems[3],
    navItems[7],
  ]

  return (
    <div className="min-h-screen bg-gray-900 text-white flex">
      {/* PC 사이드바 */}
      <aside className="hidden md:flex flex-col w-64 min-h-screen bg-gray-800 border-r border-gray-700 fixed top-0 left-0 z-20">
        {/* 로고 */}
        <div className="px-6 py-5 border-b border-gray-700">
          <span className="text-xl font-bold text-white">🏠 부산 내집마련</span>
        </div>
        {/* 메뉴 */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <SidebarLink key={item.path} {...item} />
          ))}
        </nav>
        <div className="px-4 py-4 border-t border-gray-700 text-xs text-gray-500">
          v0.1.0 · 매일 00:00 갱신
        </div>
      </aside>

      {/* 모바일 헤더 */}
      <header className="md:hidden fixed top-0 left-0 right-0 z-20 bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center">
        <span className="text-lg font-bold text-white">🏠 부산 내집마련</span>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="flex-1 md:ml-64 min-h-screen">
        {/* 모바일 상단 헤더 높이만큼 패딩 */}
        <div className="pt-14 md:pt-0 pb-20 md:pb-0 px-4 md:px-8 py-6 md:py-8">
          {children}
        </div>
      </main>

      {/* 모바일 하단 탭바 */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-20 bg-gray-800 border-t border-gray-700 flex justify-around items-center py-1">
        {mobileNavItems.map((item) => (
          <BottomTabLink key={item.path} {...item} />
        ))}
      </nav>
    </div>
  )
}
