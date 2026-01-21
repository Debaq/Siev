import { useState, useCallback, useEffect } from 'react'

interface HealthResponse {
  status: string
  video_status: string
  hardware_status: string
  uptime: number
}

interface UseBackendReturn {
  health: HealthResponse | null
  isConnected: boolean
  isLoading: boolean
  error: string | null
  checkHealth: () => Promise<void>
  fetchApi: <T>(endpoint: string, options?: RequestInit) => Promise<T | null>
}

export function useBackend(apiUrl: string): UseBackendReturn {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchApi = useCallback(async <T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T | null> => {
    try {
      const response = await fetch(`${apiUrl}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json() as T
    } catch (err) {
      console.error(`API Error (${endpoint}):`, err)
      return null
    }
  }, [apiUrl])

  const checkHealth = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${apiUrl}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      })

      if (response.ok) {
        const data = await response.json() as HealthResponse
        setHealth(data)
        setIsConnected(data.status === 'ok')
      } else {
        setIsConnected(false)
        setError('Backend returned error status')
      }
    } catch (err) {
      setIsConnected(false)
      setHealth(null)
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Failed to connect to backend')
      }
    } finally {
      setIsLoading(false)
    }
  }, [apiUrl])

  // Initial health check
  useEffect(() => {
    checkHealth()
  }, [checkHealth])

  return {
    health,
    isConnected,
    isLoading,
    error,
    checkHealth,
    fetchApi,
  }
}

export default useBackend
