import { useState, useRef, useEffect } from 'react'
import {
  Play, Square, Circle, Crosshair,
  Cpu, Lightbulb, LightbulbOff,
  Sun, Activity, Eye, Settings, X, RotateCcw
} from 'lucide-react'
import { useTauriHardware } from '../hooks/useTauriHardware'
import { UseSessionConfigReturn } from '../hooks/useSessionConfig'
import { useWebSocket } from '../contexts/WebSocketContext'

interface ControlPanelProps {
  isCapturing: boolean
  onStartCapture: () => void
  onStopCapture: () => void
  onCalibrate: () => void
  sessionConfig: UseSessionConfigReturn
  appConfig: any
  currentSession?: any
}

function ControlPanel({
  isCapturing,
  onStartCapture,
  onStopCapture,
  onCalibrate,
  sessionConfig,
  appConfig,
  currentSession
}: ControlPanelProps) {
  const { send, hardwareStatus: _wsHardwareStatus } = useWebSocket()
  const [isRecording, setIsRecording] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const advancedPanelRef = useRef<HTMLDivElement>(null)

  // Extract values and methods from sessionConfig
  const { values, hasOverrides, updateAndSync, clearAllOverrides } = sessionConfig
  const { brightness, contrast, threshold, erode, nose_width, eye_height, use_yolo, show_debug } = values

  // Close panel on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (advancedPanelRef.current && !advancedPanelRef.current.contains(event.target as Node)) {
        setShowAdvanced(false)
      }
    }
    if (showAdvanced) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showAdvanced])

  // Tauri Hardware
  const { controlLed, isConnected: isHwConnected } = useTauriHardware(appConfig)

  // Handlers that update session config and sync to backend via WebSocket
  const handleBrightnessChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value)
    updateAndSync('brightness', val)
    send({ type: 'set_config', key: 'brightness', value: val })
  }

  const handleContrastChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value)
    updateAndSync('contrast', val)
    send({ type: 'set_config', key: 'contrast', value: val })
  }

  const handleThresholdChange = (eye: 'right' | 'left', val: number) => {
    const newThreshold: [number, number] = eye === 'right'
      ? [val, threshold[1]]
      : [threshold[0], val]
    updateAndSync('threshold', newThreshold)
    send({ type: 'set_config', key: 'threshold', value: newThreshold })
  }

  const handleErodeChange = (eye: 'right' | 'left', val: number) => {
    const newErode: [number, number] = eye === 'right'
      ? [val, erode[1]]
      : [erode[0], val]
    updateAndSync('erode', newErode)
    send({ type: 'set_config', key: 'erode', value: newErode })
  }

  const handleNoseWidthChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value)
    updateAndSync('nose_width', val)
    send({ type: 'set_config', key: 'nose_width', value: val })
  }

  const handleEyeHeightChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value)
    updateAndSync('eye_height', val)
    send({ type: 'set_config', key: 'eye_height', value: val })
  }

  const handleToggleYolo = () => {
    const val = !use_yolo
    updateAndSync('use_yolo', val)
    send({ type: 'set_config', key: 'use_yolo', value: val })
  }

  const handleToggleDebug = () => {
    const val = !show_debug
    updateAndSync('show_debug', val)
    send({ type: 'set_config', key: 'show_debug', value: val })
  }

  const handleStartRecording = () => {
    if (currentSession) {
      send({ type: 'start_recording', session_id: currentSession.id })
    } else {
      // Fallback for "free capture" if needed, but here we require a session
      send({ type: 'send_command', cmd: 'start_recording' })
    }
    setIsRecording(true)
  }

  const handleStopRecording = () => {
    send({ type: 'stop_recording' })
    setIsRecording(false)
  }

  const handleResetToConfig = () => {
    clearAllOverrides()
    // In a real scenario, we would send all default values back
  }

  const handleLed = async (led: string, action: 'on' | 'off') => {
    const ledType = led as 'left' | 'right' | 'all'
    await controlLed(ledType, action)
  }

  const SectionTitle = ({ icon: Icon, title }: { icon: any, title: string }) => (
    <div className="flex items-center gap-1.5 text-[10px] uppercase font-bold text-dark-400 mt-4 mb-2 pl-1">
      <Icon className="w-3 h-3" />
      <span>{title}</span>
    </div>
  )

  return (
    <div className="flex flex-col h-full relative">
      {/* Header with Title and Settings Toggle */}
      <div className="flex justify-between items-center mb-3">
        <h2 className="text-xs font-bold text-dark-300 uppercase tracking-wider">Control VNG</h2>
        <button 
          onClick={() => setShowAdvanced(!showAdvanced)}
          className={`p-1.5 rounded-lg transition-all ${showAdvanced ? 'bg-siev-500 text-white shadow-lg shadow-siev-500/20' : 'text-dark-400 hover:bg-dark-800 hover:text-white'}`}
          title="Ajustes Avanzados"
        >
          <Settings className={`w-4 h-4 ${showAdvanced ? 'animate-spin-slow' : ''}`} />
        </button>
      </div>

      {/* Advanced Panel Overlay/Roll-down */}
      {showAdvanced && (
        <div 
          ref={advancedPanelRef}
          className="absolute top-10 left-0 right-0 z-30 bg-dark-900 border border-dark-700 rounded-xl shadow-2xl p-4 animate-in slide-in-from-top-2 duration-200"
        >
          <div className="flex justify-between items-center mb-2">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-siev-400 uppercase tracking-widest">Ajustes Avanzados</span>
              {hasOverrides && (
                <span className="text-[8px] bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded-full">
                  Temporales
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              {hasOverrides && (
                <button
                  onClick={handleResetToConfig}
                  className="text-dark-400 hover:text-yellow-400 p-1 rounded hover:bg-dark-700"
                  title="Restaurar valores de configuración"
                >
                  <RotateCcw className="w-3 h-3" />
                </button>
              )}
              <button onClick={() => setShowAdvanced(false)} className="text-dark-500 hover:text-white">
                <X className="w-3 h-3" />
              </button>
            </div>
          </div>

          <div className="max-h-[350px] overflow-y-auto pr-1 custom-scrollbar">
            {/* Image Settings */}
            <SectionTitle icon={Sun} title="Imagen" />
            <div className="space-y-3 px-1">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                    <span>Brillo</span>
                    <span>{brightness}</span>
                  </div>
                  <input
                    type="range"
                    min="-64" max="64"
                    className="w-full accent-siev-500"
                    value={brightness}
                    onChange={handleBrightnessChange}
                  />
                </div>
                <div>
                  <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                    <span>Contraste</span>
                    <span>{contrast}</span>
                  </div>
                  <input
                    type="range"
                    min="0" max="100"
                    className="w-full accent-siev-500"
                    value={contrast}
                    onChange={handleContrastChange}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                    <span>Umbral Der</span>
                    <span>{threshold[0]}</span>
                  </div>
                  <input
                    type="range"
                    min="0" max="255"
                    className="w-full accent-siev-500"
                    value={threshold[0]}
                    onChange={(e) => handleThresholdChange('right', Number(e.target.value))}
                  />
                </div>
                <div>
                  <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                    <span>Umbral Izq</span>
                    <span>{threshold[1]}</span>
                  </div>
                  <input
                    type="range"
                    min="0" max="255"
                    className="w-full accent-siev-500"
                    value={threshold[1]}
                    onChange={(e) => handleThresholdChange('left', Number(e.target.value))}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                    <span>Erosión Der</span>
                    <span>{erode[0]}</span>
                  </div>
                  <input
                    type="range"
                    min="0" max="10"
                    className="w-full accent-siev-500"
                    value={erode[0]}
                    onChange={(e) => handleErodeChange('right', Number(e.target.value))}
                  />
                </div>
                <div>
                  <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                    <span>Erosión Izq</span>
                    <span>{erode[1]}</span>
                  </div>
                  <input
                    type="range"
                    min="0" max="10"
                    className="w-full accent-siev-500"
                    value={erode[1]}
                    onChange={(e) => handleErodeChange('left', Number(e.target.value))}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                    <span>Ancho Nariz</span>
                    <span>{nose_width.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="0.05" max="0.5" step="0.01"
                    className="w-full accent-siev-500"
                    value={nose_width}
                    onChange={handleNoseWidthChange}
                  />
                </div>
                <div>
                  <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                    <span>Altura Ojo</span>
                    <span>{eye_height.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="0.05" max="0.5" step="0.01"
                    className="w-full accent-siev-500"
                    value={eye_height}
                    onChange={handleEyeHeightChange}
                  />
                </div>
              </div>
            </div>

            {/* Detection */}
            <SectionTitle icon={Cpu} title="Procesamiento" />
            <div className="px-1 space-y-2 pb-2">
              <button
                className={`w-full btn ${use_yolo ? 'btn-primary' : 'btn-secondary'} justify-between px-3 h-8`}
                onClick={handleToggleYolo}
              >
                <span className="text-[10px]">Detección IA (YOLO)</span>
                <div className={`w-2 h-2 rounded-full ${use_yolo ? 'bg-white' : 'bg-dark-500'}`} />
              </button>

              <button
                className={`w-full btn ${show_debug ? 'btn-success' : 'btn-secondary'} justify-between px-3 h-8`}
                onClick={handleToggleDebug}
              >
                <div className="flex items-center gap-1">
                  <Eye className="w-3 h-3" />
                  <span className="text-[10px]">Modo Debug</span>
                </div>
                <div className={`w-2 h-2 rounded-full ${show_debug ? 'bg-white' : 'bg-dark-500'}`} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Actions */}
      <div className="grid grid-cols-2 gap-2 mb-2">
        <button
          className={`btn ${isCapturing ? 'btn-danger' : 'btn-primary'} col-span-2`}
          onClick={isCapturing ? onStopCapture : onStartCapture}
        >
          {isCapturing ? <Square className="w-3 h-3" /> : <Play className="w-3 h-3" />}
          {isCapturing ? 'DETENER' : 'INICIAR CAPTURA'}
        </button>

        <button
          className={`btn ${isRecording ? 'btn-danger' : 'btn-secondary'}`}
          onClick={isRecording ? handleStopRecording : handleStartRecording}
          disabled={!isCapturing}
        >
          <Circle className={`w-3 h-3 ${isRecording ? 'fill-current animate-pulse' : ''}`} />
          {isRecording ? 'STOP REC' : 'GRABAR'}
        </button>

        <button
          className="btn btn-secondary"
          onClick={onCalibrate}
          disabled={!isCapturing}
        >
          <Crosshair className="w-3 h-3" />
          CALIBRAR
        </button>
      </div>

      <div className="border-t border-dark-800 my-1" />

      {/* Hardware (Always visible as it's critical during capture) */}
      <SectionTitle icon={Activity} title="Hardware" />
      <div className="px-1 space-y-2">
        <div className="grid grid-cols-2 gap-2">
           {/* Left LED */}
           <div className="bg-dark-800 rounded p-1.5 flex flex-col gap-1 border border-dark-700">
              <span className="text-[9px] text-center text-dark-400">LED IZQ</span>
              <div className="flex gap-1">
                <button 
                  className="btn btn-secondary flex-1 p-0 h-6" 
                  onClick={() => handleLed('left', 'on')}
                  disabled={!isHwConnected}
                >
                  <Lightbulb className="w-3 h-3 text-yellow-400" />
                </button>
                <button 
                  className="btn btn-secondary flex-1 p-0 h-6"
                  onClick={() => handleLed('left', 'off')}
                  disabled={!isHwConnected}
                >
                  <LightbulbOff className="w-3 h-3" />
                </button>
              </div>
           </div>
           
           {/* Right LED */}
           <div className="bg-dark-800 rounded p-1.5 flex flex-col gap-1 border border-dark-700">
              <span className="text-[9px] text-center text-dark-400">LED DER</span>
              <div className="flex gap-1">
                <button 
                  className="btn btn-secondary flex-1 p-0 h-6" 
                  onClick={() => handleLed('right', 'on')}
                  disabled={!isHwConnected}
                >
                  <Lightbulb className="w-3 h-3 text-yellow-400" />
                </button>
                <button 
                  className="btn btn-secondary flex-1 p-0 h-6"
                  onClick={(e) => { e.stopPropagation(); handleLed('right', 'off') }}
                  disabled={!isHwConnected}
                >
                  <LightbulbOff className="w-3 h-3" />
                </button>
              </div>
           </div>
        </div>
        <button
            className="btn btn-secondary w-full text-[10px] h-6"
            onClick={() => handleLed('all', 'off')}
            disabled={!isHwConnected}
          >
            APAGAR TODOS
          </button>
      </div>
    </div>
  )
}

export default ControlPanel
