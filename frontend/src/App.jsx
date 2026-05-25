import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Subscriptions from './pages/Subscriptions'
import Transactions from './pages/Transactions'
import Market from './pages/Market'
import News from './pages/News'
import Policy from './pages/Policy'
import Calculator from './pages/Calculator'
import Settings from './pages/Settings'

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center">
      <p className="text-6xl">🏠</p>
      <h1 className="text-2xl font-bold text-white">페이지를 찾을 수 없습니다</h1>
      <p className="text-gray-400">요청하신 페이지가 존재하지 않습니다.</p>
    </div>
  )
}

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/subscriptions" element={<Subscriptions />} />
        <Route path="/transactions" element={<Transactions />} />
        <Route path="/market" element={<Market />} />
        <Route path="/news" element={<News />} />
        <Route path="/policy" element={<Policy />} />
        <Route path="/calculator" element={<Calculator />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Layout>
  )
}
