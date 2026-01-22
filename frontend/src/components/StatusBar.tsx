import { Activity, Wifi, WifiOff, Video, Cpu, CircleDot } from 'lucide-react'

interface StatusBarProps {
  isConnected: boolean
  videoStatus: 'offline' | 'online' | 'error'
  hardwareStatus: 'offline' | 'online' | 'error'
  fps: number
  recording: boolean
}

function StatusBar({
  isConnected,
  videoStatus,
  hardwareStatus,
  fps,
  recording,
}: StatusBarProps) {
  const getStatusColor = (status: 'offline' | 'online' | 'error') => {
    switch (status) {
      case 'online':
        return 'text-green-400'
      case 'error':
        return 'text-red-400'
      default:
        return 'text-dark-400'
    }
  }

  const getStatusDotClass = (status: 'offline' | 'online' | 'error') => {
    switch (status) {
      case 'online':
        return 'status-dot-online'
      case 'error':
        return 'status-dot-offline'
      default:
        return 'bg-dark-500'
    }
  }

  return (
    <header className="bg-dark-900 border-b border-dark-800 px-4 py-2">
      <div className="flex items-center justify-between">
        {/* Logo & Title */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-siev-600 rounded-lg flex items-center justify-center">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white">SIEV</h1>
            <p className="text-xs text-dark-400">Video-Oculografía</p>
          </div>
        </div>

        {/* Status Indicators */}
        <div className="flex items-center gap-6">
          {/* Backend Connection */}
          <div className="flex items-center gap-2">
            {isConnected ? (
              <Wifi className="w-4 h-4 text-green-400" />
            ) : (
              <WifiOff className="w-4 h-4 text-red-400" />
            )}
            <span className={`text-sm ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
              {isConnected ? 'Conectado' : 'Desconectado'}
            </span>
          </div>

          {/* Divider */}
          <div className="w-px h-6 bg-dark-700" />

          {/* Video Status */}
          <div className="flex items-center gap-2">
            <Video className={`w-4 h-4 ${getStatusColor(videoStatus)}`} />
            <div className="flex items-center gap-1.5">
              <span className={`status-dot ${getStatusDotClass(videoStatus)}`} />
              <span className={`text-sm ${getStatusColor(videoStatus)}`}>
                Video
              </span>
            </div>
          </div>

          {/* Hardware Status */}
          <div className="flex items-center gap-2">
            <Cpu className={`w-4 h-4 ${getStatusColor(hardwareStatus)}`} />
            <div className="flex items-center gap-1.5">
              <span className={`status-dot ${getStatusDotClass(hardwareStatus)}`} />
              <span className={`text-sm ${getStatusColor(hardwareStatus)}`}>
                IMU
              </span>
            </div>
          </div>

          {/* FPS */}
          {fps > 0 && (
            <>
              <div className="w-px h-6 bg-dark-700" />
              <div className="flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-siev-400" />
                <span className="text-sm text-siev-400 font-mono">
                  {fps.toFixed(1)} FPS
                </span>
              </div>
            </>
          )}

          {/* Recording Indicator */}
          {recording && (
            <>
              <div className="w-px h-6 bg-dark-700" />
              <div className="flex items-center gap-1.5 text-red-400">
                <CircleDot className="w-4 h-4 animate-pulse" />
                <span className="text-sm font-medium">REC</span>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}

export default StatusBar
