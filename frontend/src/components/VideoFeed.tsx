import { useState, useEffect, useRef, useCallback } from 'react'
import { Video, VideoOff, AlertCircle } from 'lucide-react'

interface VideoFeedProps {
  apiUrl: string
  isCapturing: boolean
}

function VideoFeed({ apiUrl, isCapturing }: VideoFeedProps) {
  const [error, setError] = useState<string | null>(null)
  const [imageKey, setImageKey] = useState(0)
  const lastReconnectRef = useRef<number>(0)

  // Force reconnection to video stream
  const forceReconnect = useCallback(async () => {
    // Debounce: prevent multiple reconnects within 500ms
    const now = Date.now()
    if (now - lastReconnectRef.current < 500) return
    lastReconnectRef.current = now

    if (!isCapturing) return

    try {
      // Reset stream on backend to clear stale frames
      await fetch(`${apiUrl}/video/reset_stream`, { method: 'POST' })
      // Force remount of img element with new key
      setError(null)
      setImageKey(prev => prev + 1)
    } catch (e) {
      console.warn('Failed to reset stream:', e)
      // Still try to reconnect even if reset fails
      setImageKey(prev => prev + 1)
    }
  }, [apiUrl, isCapturing])

  // Reset image on capture state change
  useEffect(() => {
    if (isCapturing) {
      setError(null)
      setImageKey(prev => prev + 1)
    }
  }, [isCapturing])

  // Detect reconnection scenarios (hot-reload, tab switch, window focus)
  useEffect(() => {
    if (!isCapturing) return

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        forceReconnect()
      }
    }

    const handleFocus = () => {
      forceReconnect()
    }

    // For Tauri hot-reload detection
    const handlePageShow = (event: PageTransitionEvent) => {
      if (event.persisted) {
        forceReconnect()
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('focus', handleFocus)
    window.addEventListener('pageshow', handlePageShow)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('focus', handleFocus)
      window.removeEventListener('pageshow', handlePageShow)
    }
  }, [isCapturing, forceReconnect])

  const handleImageError = () => {
    setError('Error loading video stream')
  }

  if (!isCapturing) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <div className="text-center text-dark-400">
          <VideoOff className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium">Video no iniciado</p>
          <p className="text-sm mt-1">Presiona "Iniciar Captura" para comenzar</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <div className="text-center text-red-400">
          <AlertCircle className="w-16 h-16 mx-auto mb-4" />
          <p className="text-lg font-medium">Error de conexión</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full h-full relative flex items-center justify-center">
      <img
        key={imageKey}
        src={`${apiUrl}/video_feed`}
        alt="Video Feed"
        className="max-w-full max-h-full object-contain"
        onError={handleImageError}
      />
      {/* Video overlay with status */}
      <div className="absolute top-2 left-2 flex items-center gap-2">
        <div className="glass px-2 py-1 rounded flex items-center gap-2">
          <Video className="w-4 h-4 text-green-400" />
          <span className="text-xs text-green-400">LIVE</span>
        </div>
      </div>
    </div>
  )
}

export default VideoFeed
