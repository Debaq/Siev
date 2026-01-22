import { Video, VideoOff } from 'lucide-react'
import { useWebSocket } from '../contexts/WebSocketContext'

interface VideoFeedProps {
  isCapturing: boolean
}

function VideoFeed({ isCapturing }: VideoFeedProps) {
  const { videoFrame } = useWebSocket()

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

  return (
    <div className="w-full h-full relative flex items-center justify-center">
      {videoFrame ? (
        <img
          src={`data:image/jpeg;base64,${videoFrame}`}
          alt="Video Feed"
          className="max-w-full max-h-full object-contain"
        />
      ) : (
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-2 border-siev-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-dark-400">Esperando señal...</span>
        </div>
      )}
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