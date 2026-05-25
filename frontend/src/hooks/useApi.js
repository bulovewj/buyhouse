import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'

export function useFetch(url, params = {}) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await axios.get(url, { params })
      setData(res.data)
    } catch (e) {
      console.error(`API 요청 실패 [${url}]:`, e.message)
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [url, JSON.stringify(params)])

  useEffect(() => { fetch() }, [fetch])

  return { data, loading, error, refetch: fetch }
}
