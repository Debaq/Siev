import { useState, useEffect, useRef, useCallback } from 'react'

interface UseSSEOptions<T> {
  url: string
  enabled?: boolean
  onData?: (data: T) => void
  onError?: (error: Event) => void
  onOpen?: () => void
}

interface UseSSEReturn<T> {
  data: T | null
  isConnected: boolean
  error: Event | null
  reconnect: () => void
}

export function useSSE<T>({
  url,
  enabled = true,
  onData,
  onError,
  onOpen,
}: UseSSEOptions<T>): UseSSEReturn<T> {
  const [data, setData] = useState<T | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<Event | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  const connect = useCallback(() => {
    if (!enabled || eventSourceRef.current) return

    const eventSource = new EventSource(url)
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      setIsConnected(true)
      setError(null)
      onOpen?.()
    }

    eventSource.onmessage = (event) => {
      try {
        const parsedData = JSON.parse(event.data) as T
        setData(parsedData)
        onData?.(parsedData)
      } catch (err) {
        console.error('Error parsing SSE data:', err)
      }
    }

    eventSource.onerror = (err) => {
      setIsConnected(false)
      setError(err)
      onError?.(err)

      // Close and cleanup on error
      eventSource.close()
      eventSourceRef.current = null
    }
  }, [url, enabled, onData, onError, onOpen])

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
      setIsConnected(false)
    }
  }, [])

  const reconnect = useCallback(() => {
    disconnect()
    connect()
  }, [disconnect, connect])

  useEffect(() => {
    if (enabled) {
      connect()
    } else {
      disconnect()
    }

    return () => {
      disconnect()
    }
  }, [enabled, connect, disconnect])

  return {
    data,
    isConnected,
    error,
    reconnect,
  }
}

export default useSSE
