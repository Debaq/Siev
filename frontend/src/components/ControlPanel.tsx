import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Circle, Crosshair,
  Cpu, Lightbulb, LightbulbOff,
  Sun, Activity, Eye, Settings, X, RotateCcw, ChevronDown,
  Check, Plus, Thermometer, Minus, ShieldOff, AlertTriangle, Target
} from 'lucide-react'
import { useTauriHardware } from '../hooks/useTauriHardware'
import { UseSessionConfigReturn } from '../hooks/useSessionConfig'
import { UseCaloricProtocolReturn } from '../hooks/useCaloricProtocol'
import { computeCompletionStatus, CompletionStatus } from '../hooks/useCaloricTimer'
import { CaloricProtocolTiming } from '../types/config'
import { useWebSocket } from '../contexts/WebSocketContext'
import { StimulusController } from './StimulusController'

interface AccordionSectionProps {
  id: string
  icon: any
  title: string
  badge?: { label: string; color: string }
  children: React.ReactNode
  openSection: string
  onToggle: (id: string) => void
}

function AccordionSection({ id, icon: Icon, title, badge, children, openSection, onToggle }: AccordionSectionProps) {
  const isOpen = openSection === id
  return (
    <div className="border-b border-dark-700/50">
      <button
        onClick={() => onToggle(id)}
        className="flex items-center justify-between w-full py-2 px-1 text-left hover:bg-dark-800/50 transition-colors rounded"
      >
        <div className="flex items-center gap-1.5">
          <Icon className="w-3 h-3 text-dark-400" />
          <span className="text-[10px] uppercase font-bold text-dark-400">{title}</span>
          {badge && (
            <span className="text-[8px] font-bold px-1.5 py-0.5 rounded-full" style={{ backgroundColor: `${badge.color}20`, color: badge.color }}>
              {badge.label}
            </span>
          )}
        </div>
        <ChevronDown className={`w-3 h-3 text-dark-500 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      <div
        className={`overflow-hidden transition-all duration-200 ${isOpen ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'}`}
      >
        <div className="pb-3 px-1">{children}</div>
      </div>
    </div>
  )
}

interface ControlPanelProps {
  isCapturing: boolean
  onCalibrate: () => void
  sessionConfig: UseSessionConfigReturn
  appConfig: any
  currentSession?: any
  currentRecording?: any
  currentTestType?: string | null
  caloricProtocol?: UseCaloricProtocolReturn
  isRecording: boolean
  onRecordingChange: (v: boolean) => void
  onStartRecording?: () => Promise<void> | void
  isCalibrated: boolean
  onBypassCalibration: () => void
  onReviewSession?: () => void
  caloricTimerInfo?: { elapsedSeconds: number; timing: CaloricProtocolTiming }
  onRedoStage?: (index: number) => void
}

function ControlPanel({
  isCapturing,
  onCalibrate,
  sessionConfig,
  appConfig,
  currentRecording,
  currentTestType,
  caloricProtocol,
  isRecording,
  onRecordingChange,
  onStartRecording,
  isCalibrated,
  onBypassCalibration,
  onReviewSession,
  caloricTimerInfo,
  onRedoStage,
}: ControlPanelProps) {
  const { send } = useWebSocket()
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [showAddStage, setShowAddStage] = useState(false)
  const [newStageTemp, setNewStageTemp] = useState<number>(40)
  const [newStageEar, setNewStageEar] = useState<'od' | 'oi'>('od')
  const [openSection, setOpenSection] = useState<string>('image')
  const advancedPanelRef = useRef<HTMLDivElement>(null)
  const [showBypass, setShowBypass] = useState(false)
  const bypassTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Spinner hold logic for temperature
  const holdIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const holdCountRef = useRef(0)

  const clearHold = useCallback(() => {
    if (holdIntervalRef.current) {
      clearInterval(holdIntervalRef.current)
      holdIntervalRef.current = null
    }
    holdCountRef.current = 0
  }, [])

  const startHold = useCallback((direction: 1 | -1) => {
    clearHold()
    holdIntervalRef.current = setInterval(() => {
      holdCountRef.current += 1
      const step = holdCountRef.current > 5 ? 5 : 1
      setNewStageTemp(prev => Math.max(1, Math.min(55, prev + direction * step)))
    }, 150)
  }, [clearHold])

  useEffect(() => {
    // Cleanup on unmount
    return clearHold
  }, [clearHold])

  // Extract values and methods from sessionConfig
  const { values, hasOverrides, updateAndSync, clearAllOverrides } = sessionConfig
  const { brightness, contrast, threshold, nose_width, eye_height, use_yolo, show_debug, smooth, manual_roi_right, manual_roi_left, min_circularity, min_area, blink_detection, blink_white_ratio, lost_tolerance, velocity_margin_factor, aspect_ratio_min, aspect_ratio_max } = values

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

  const handleSmoothChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value)
    updateAndSync('smooth', val)
    send({ type: 'set_config', key: 'smooth', value: val })
  }

  const handleRoiChange = (eye: 'right' | 'left', param: 'top' | 'bottom' | 'nasal' | 'temporal', value: number) => {
    const currentRoi = eye === 'right' ? manual_roi_right : manual_roi_left
    const newRoi = { ...currentRoi, [param]: value }
    const key = eye === 'right' ? 'manual_roi_right' : 'manual_roi_left'
    updateAndSync(key, newRoi)
    send({ type: 'set_config', key, value: newRoi })
  }

  const handleTrackingChange = (key: string, value: number | boolean) => {
    updateAndSync(key as any, value)
    send({ type: 'set_config', key, value })
  }

  const handleStartRecording = async () => {
    if (onStartRecording) {
      await onStartRecording()
    } else if (currentRecording) {
      send({ type: 'start_recording', recording_id: currentRecording.id })
      onRecordingChange(true)
    } else {
      send({ type: 'send_command', cmd: 'start_recording' })
      onRecordingChange(true)
    }
  }

  const handleStopRecording = () => {
    send({ type: 'stop_recording' })
    onRecordingChange(false)
    if (caloricProtocol && caloricProtocol.isProtocolActive) {
      let status: CompletionStatus | undefined
      if (caloricTimerInfo) {
        status = computeCompletionStatus(caloricTimerInfo.elapsedSeconds, caloricTimerInfo.timing)
      }
      caloricProtocol.advanceStage(status)
    }
  }

  const handleAddStage = () => {
    if (!caloricProtocol) return
    caloricProtocol.addStage({
      label: `${newStageTemp}°C ${newStageEar.toUpperCase()}`,
      temperature: newStageTemp,
      ear: newStageEar,
    })
    setShowAddStage(false)
  }

  const handleResetToConfig = () => {
    clearAllOverrides()
    // In a real scenario, we would send all default values back
  }

  const handleLed = async (led: string, action: 'on' | 'off') => {
    const ledType = led as 'left' | 'right' | 'all'
    await controlLed(ledType, action)
  }

  /** Compute CSS vars for colored track fill */
  const sliderStyle = (value: number, min: number, max: number, color?: string): React.CSSProperties => {
    const pct = ((value - min) / (max - min)) * 100
    return {
      '--val-pct': `${pct}%`,
      ...(color ? { '--slider-color': color } : {}),
    } as React.CSSProperties
  }

  const toggleSection = (id: string) => setOpenSection(prev => prev === id ? '' : id)

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

          <div className="max-h-[400px] overflow-y-auto pr-1 custom-scrollbar">
            {/* === Imagen === */}
            <AccordionSection id="image" icon={Sun} title="Imagen" openSection={openSection} onToggle={toggleSection}>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                      <span>Brillo</span>
                      <span>{brightness}</span>
                    </div>
                    <input
                      type="range"
                      min="-64" max="64"
                      className="w-full"
                      value={brightness}
                      onChange={handleBrightnessChange}
                      style={sliderStyle(brightness, -64, 64)}
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
                      className="w-full"
                      value={contrast}
                      onChange={handleContrastChange}
                      style={sliderStyle(contrast, 0, 100)}
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
                      className="w-full"
                      value={threshold[0]}
                      onChange={(e) => handleThresholdChange('right', Number(e.target.value))}
                      style={sliderStyle(threshold[0], 0, 255)}
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
                      className="w-full"
                      value={threshold[1]}
                      onChange={(e) => handleThresholdChange('left', Number(e.target.value))}
                      style={sliderStyle(threshold[1], 0, 255)}
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
                      className="w-full"
                      value={nose_width}
                      onChange={handleNoseWidthChange}
                      style={sliderStyle(nose_width, 0.05, 0.5)}
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
                      className="w-full"
                      value={eye_height}
                      onChange={handleEyeHeightChange}
                      style={sliderStyle(eye_height, 0.05, 0.5)}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                    <span>Suavizado</span>
                    <span>{smooth.toFixed(1)}</span>
                  </div>
                  <input
                    type="range"
                    min="0.5" max="10" step="0.5"
                    className="w-full"
                    value={smooth}
                    onChange={handleSmoothChange}
                    style={sliderStyle(smooth, 0.5, 10)}
                  />
                </div>
              </div>
            </AccordionSection>

            {/* === Tracking === */}
            <AccordionSection id="tracking" icon={Target} title="Tracking" openSection={openSection} onToggle={toggleSection}>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                      <span>Circularidad mín</span>
                      <span>{min_circularity.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min="0.2" max="0.9" step="0.05"
                      className="w-full"
                      value={min_circularity}
                      onChange={(e) => handleTrackingChange('min_circularity', parseFloat(e.target.value))}
                      style={sliderStyle(min_circularity, 0.2, 0.9)}
                    />
                  </div>
                  <div>
                    <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                      <span>Área mínima</span>
                      <span>{min_area}</span>
                    </div>
                    <input
                      type="range"
                      min="10" max="200" step="5"
                      className="w-full"
                      value={min_area}
                      onChange={(e) => handleTrackingChange('min_area', Number(e.target.value))}
                      style={sliderStyle(min_area, 10, 200)}
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-dark-400">Detección de parpadeo</span>
                  <button
                    className={`w-8 h-4 rounded-full transition-colors relative ${blink_detection ? 'bg-siev-500' : 'bg-dark-600'}`}
                    onClick={() => handleTrackingChange('blink_detection', !blink_detection)}
                  >
                    <div className={`w-3 h-3 rounded-full bg-white absolute top-0.5 transition-transform ${blink_detection ? 'translate-x-4' : 'translate-x-0.5'}`} />
                  </button>
                </div>

                {blink_detection && (
                  <div>
                    <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                      <span>Sensibilidad parpadeo</span>
                      <span>{blink_white_ratio.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min="0.3" max="0.9" step="0.05"
                      className="w-full"
                      value={blink_white_ratio}
                      onChange={(e) => handleTrackingChange('blink_white_ratio', parseFloat(e.target.value))}
                      style={sliderStyle(blink_white_ratio, 0.3, 0.9)}
                    />
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                      <span>Tolerancia pérdida</span>
                      <span>{lost_tolerance}</span>
                    </div>
                    <input
                      type="range"
                      min="2" max="30" step="1"
                      className="w-full"
                      value={lost_tolerance}
                      onChange={(e) => handleTrackingChange('lost_tolerance', Number(e.target.value))}
                      style={sliderStyle(lost_tolerance, 2, 30)}
                    />
                  </div>
                  <div>
                    <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                      <span>Factor velocidad</span>
                      <span>{velocity_margin_factor.toFixed(1)}</span>
                    </div>
                    <input
                      type="range"
                      min="0.5" max="5" step="0.5"
                      className="w-full"
                      value={velocity_margin_factor}
                      onChange={(e) => handleTrackingChange('velocity_margin_factor', parseFloat(e.target.value))}
                      style={sliderStyle(velocity_margin_factor, 0.5, 5)}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                      <span>Aspect ratio mín</span>
                      <span>{aspect_ratio_min.toFixed(1)}</span>
                    </div>
                    <input
                      type="range"
                      min="0.1" max="1" step="0.1"
                      className="w-full"
                      value={aspect_ratio_min}
                      onChange={(e) => handleTrackingChange('aspect_ratio_min', parseFloat(e.target.value))}
                      style={sliderStyle(aspect_ratio_min, 0.1, 1)}
                    />
                  </div>
                  <div>
                    <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                      <span>Aspect ratio máx</span>
                      <span>{aspect_ratio_max.toFixed(1)}</span>
                    </div>
                    <input
                      type="range"
                      min="1" max="5" step="0.1"
                      className="w-full"
                      value={aspect_ratio_max}
                      onChange={(e) => handleTrackingChange('aspect_ratio_max', parseFloat(e.target.value))}
                      style={sliderStyle(aspect_ratio_max, 1, 5)}
                    />
                  </div>
                </div>
              </div>
            </AccordionSection>

            {/* === ROI Ojo Derecho (solo sin YOLO) === */}
            {!use_yolo && (
              <AccordionSection id="roi-right" icon={Eye} title="ROI Ojo Derecho" badge={{ label: 'OD', color: '#ef4444' }} openSection={openSection} onToggle={toggleSection}>
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                        <span>Superior</span>
                        <span>{manual_roi_right.top.toFixed(2)}</span>
                      </div>
                      <input
                        type="range" min="0" max="0.5" step="0.01"
                        className="w-full"
                        value={manual_roi_right.top}
                        onChange={(e) => handleRoiChange('right', 'top', parseFloat(e.target.value))}
                        style={sliderStyle(manual_roi_right.top, 0, 0.5, '#ef4444')}
                      />
                    </div>
                    <div>
                      <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                        <span>Inferior</span>
                        <span>{manual_roi_right.bottom.toFixed(2)}</span>
                      </div>
                      <input
                        type="range" min="0.5" max="1" step="0.01"
                        className="w-full"
                        value={manual_roi_right.bottom}
                        onChange={(e) => handleRoiChange('right', 'bottom', parseFloat(e.target.value))}
                        style={sliderStyle(manual_roi_right.bottom, 0.5, 1, '#ef4444')}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                        <span>Temporal</span>
                        <span>{manual_roi_right.temporal.toFixed(2)}</span>
                      </div>
                      <input
                        type="range" min="0" max="0.5" step="0.01"
                        className="w-full"
                        value={manual_roi_right.temporal}
                        onChange={(e) => handleRoiChange('right', 'temporal', parseFloat(e.target.value))}
                        style={sliderStyle(manual_roi_right.temporal, 0, 0.5, '#ef4444')}
                      />
                    </div>
                    <div>
                      <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                        <span>Nasal</span>
                        <span>{manual_roi_right.nasal.toFixed(2)}</span>
                      </div>
                      <input
                        type="range" min="0.5" max="1" step="0.01"
                        className="w-full"
                        value={manual_roi_right.nasal}
                        onChange={(e) => handleRoiChange('right', 'nasal', parseFloat(e.target.value))}
                        style={sliderStyle(manual_roi_right.nasal, 0.5, 1, '#ef4444')}
                      />
                    </div>
                  </div>
                </div>
              </AccordionSection>
            )}

            {/* === ROI Ojo Izquierdo (solo sin YOLO) === */}
            {!use_yolo && (
              <AccordionSection id="roi-left" icon={Eye} title="ROI Ojo Izquierdo" badge={{ label: 'OI', color: '#06b6d4' }} openSection={openSection} onToggle={toggleSection}>
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                        <span>Superior</span>
                        <span>{manual_roi_left.top.toFixed(2)}</span>
                      </div>
                      <input
                        type="range" min="0" max="0.5" step="0.01"
                        className="w-full"
                        value={manual_roi_left.top}
                        onChange={(e) => handleRoiChange('left', 'top', parseFloat(e.target.value))}
                        style={sliderStyle(manual_roi_left.top, 0, 0.5, '#06b6d4')}
                      />
                    </div>
                    <div>
                      <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                        <span>Inferior</span>
                        <span>{manual_roi_left.bottom.toFixed(2)}</span>
                      </div>
                      <input
                        type="range" min="0.5" max="1" step="0.01"
                        className="w-full"
                        value={manual_roi_left.bottom}
                        onChange={(e) => handleRoiChange('left', 'bottom', parseFloat(e.target.value))}
                        style={sliderStyle(manual_roi_left.bottom, 0.5, 1, '#06b6d4')}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                        <span>Nasal</span>
                        <span>{manual_roi_left.nasal.toFixed(2)}</span>
                      </div>
                      <input
                        type="range" min="0" max="0.5" step="0.01"
                        className="w-full"
                        value={manual_roi_left.nasal}
                        onChange={(e) => handleRoiChange('left', 'nasal', parseFloat(e.target.value))}
                        style={sliderStyle(manual_roi_left.nasal, 0, 0.5, '#06b6d4')}
                      />
                    </div>
                    <div>
                      <div className="flex justify-between text-[10px] text-dark-400 mb-1">
                        <span>Temporal</span>
                        <span>{manual_roi_left.temporal.toFixed(2)}</span>
                      </div>
                      <input
                        type="range" min="0.5" max="1" step="0.01"
                        className="w-full"
                        value={manual_roi_left.temporal}
                        onChange={(e) => handleRoiChange('left', 'temporal', parseFloat(e.target.value))}
                        style={sliderStyle(manual_roi_left.temporal, 0.5, 1, '#06b6d4')}
                      />
                    </div>
                  </div>
                </div>
              </AccordionSection>
            )}

            {/* === Procesamiento === */}
            <AccordionSection id="processing" icon={Cpu} title="Procesamiento" openSection={openSection} onToggle={toggleSection}>
              <div className="space-y-2">
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
            </AccordionSection>
          </div>
        </div>
      )}

      {/* Main Actions */}
      <div className="grid grid-cols-2 gap-2 mb-2">
        <button
          className={`btn ${isRecording ? 'btn-danger' : 'btn-primary'} col-span-2`}
          onClick={isRecording ? handleStopRecording : handleStartRecording}
          disabled={!isCapturing || (!isCalibrated && !isRecording)}
          title={!isCalibrated && !isRecording ? 'Se requiere calibración antes de iniciar' : undefined}
        >
          <Circle className={`w-3 h-3 ${isRecording ? 'fill-current animate-pulse' : ''}`} />
          {isRecording ? 'DETENER PRUEBA' : !isCalibrated ? 'REQUIERE CALIBRACIÓN' : 'INICIAR PRUEBA'}
        </button>

        <div className="col-span-2 flex gap-1.5 relative">
          <button
            className={`btn btn-secondary flex-1 transition-all ${showBypass ? 'rounded-r-none' : ''}`}
            onClick={onCalibrate}
            disabled={!isCapturing || isRecording}
            onMouseMove={(e) => {
              if (isCalibrated || isRecording || !isCapturing) return
              const rect = e.currentTarget.getBoundingClientRect()
              const nearRightEdge = e.clientX > rect.right - 20
              if (nearRightEdge && !bypassTimerRef.current) {
                bypassTimerRef.current = setTimeout(() => setShowBypass(true), 5000)
              } else if (!nearRightEdge && bypassTimerRef.current) {
                clearTimeout(bypassTimerRef.current)
                bypassTimerRef.current = null
              }
            }}
            onMouseLeave={() => {
              if (bypassTimerRef.current) {
                clearTimeout(bypassTimerRef.current)
                bypassTimerRef.current = null
              }
            }}
          >
            <Crosshair className="w-3 h-3" />
            CALIBRAR
          </button>
          {showBypass && !isCalibrated && (
            <button
              className="btn bg-red-600 hover:bg-red-700 text-white rounded-l-none px-2 animate-in slide-in-from-right-2 duration-200"
              onClick={() => {
                onBypassCalibration()
                setShowBypass(false)
              }}
              title="Saltar calibración"
            >
              <ShieldOff className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      <div className="border-t border-dark-800 my-1" />

      {/* Caloric Protocol Stages */}
      {caloricProtocol && caloricProtocol.stages.length > 0 && (
        <div className="mb-2">
          <SectionTitle icon={Thermometer} title="Irrigaciones" />
          <div className="px-1 space-y-1">
            {caloricProtocol.stages.map((stage, i) => {
              const cs = stage.completionStatus
              const canRedo = stage.status === 'completed' && cs && cs !== 'completada'

              return (
                <div
                  key={i}
                  onClick={() => {
                    if (isRecording) return
                    if (stage.status === 'completed' && cs === 'completada' && onReviewSession) {
                      onReviewSession()
                    } else if (stage.status === 'pending') {
                      caloricProtocol.goToStage(i)
                    }
                  }}
                  className={`flex items-center gap-2 px-2 py-1.5 rounded text-xs transition-colors ${
                    stage.status === 'active'
                      ? 'bg-green-500/15 border border-green-500/30'
                      : stage.status === 'completed' && cs === 'completada'
                      ? 'bg-dark-800/50 border border-dark-700/50 cursor-pointer hover:bg-dark-700/50'
                      : stage.status === 'completed'
                      ? 'bg-dark-800/50 border border-dark-700/50'
                      : 'bg-dark-800/30 border border-transparent cursor-pointer hover:bg-dark-800/60'
                  } ${isRecording ? 'pointer-events-none' : ''}`}
                >
                  <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold shrink-0 ${
                    stage.status === 'active'
                      ? 'bg-green-500 text-white'
                      : cs === 'completada'
                      ? 'bg-green-600 text-white'
                      : cs === 'sin_ofi'
                      ? 'bg-yellow-500 text-white'
                      : cs === 'incompleta'
                      ? 'bg-orange-500 text-white'
                      : cs === 'fallida'
                      ? 'bg-red-500 text-white'
                      : 'bg-dark-700 text-dark-400'
                  }`}>
                    {cs === 'completada' ? <Check className="w-2.5 h-2.5" />
                      : cs === 'sin_ofi' ? <Check className="w-2.5 h-2.5" />
                      : cs === 'incompleta' ? <AlertTriangle className="w-2.5 h-2.5" />
                      : cs === 'fallida' ? <X className="w-2.5 h-2.5" />
                      : i + 1}
                  </span>
                  <span className={`font-medium ${
                    stage.status === 'active'
                      ? 'text-green-400'
                      : stage.status === 'completed'
                      ? 'text-dark-400'
                      : 'text-dark-300'
                  }`}>
                    {stage.irrigation.temperature}°C {stage.irrigation.ear.toUpperCase()}
                  </span>
                  {stage.status === 'active' && (
                    <span className="ml-auto text-[9px] text-green-400 font-bold uppercase">Activa</span>
                  )}
                  {cs === 'completada' && (
                    <span className="ml-auto text-[9px] text-green-500">Completada</span>
                  )}
                  {cs === 'sin_ofi' && (
                    <span className="ml-auto text-[9px] text-yellow-400">Sin OFI</span>
                  )}
                  {cs === 'incompleta' && (
                    <span className="ml-auto text-[9px] text-orange-400">Incompleta</span>
                  )}
                  {cs === 'fallida' && (
                    <span className="ml-auto text-[9px] text-red-400">Fallida</span>
                  )}
                  {canRedo && onRedoStage && (
                    <button
                      onClick={(e) => { e.stopPropagation(); onRedoStage(i) }}
                      className="ml-1 p-0.5 rounded hover:bg-dark-600 text-dark-400 hover:text-white transition-colors"
                      title="Rehacer irrigación"
                    >
                      <RotateCcw className="w-3 h-3" />
                    </button>
                  )}
                </div>
              )
            })}

            {caloricProtocol.isProtocolComplete && (
              <div className="flex items-center gap-2 px-2 py-2 rounded bg-siev-500/10 border border-siev-500/20 text-xs text-siev-400 font-bold">
                <Check className="w-3.5 h-3.5" />
                Protocolo Completado
              </div>
            )}

            {/* Add stage button / form */}
            {!showAddStage ? (
              <button
                onClick={() => setShowAddStage(true)}
                className="flex items-center gap-1.5 px-2 py-1.5 rounded text-xs text-dark-400 hover:text-white hover:bg-dark-800 transition-colors w-full"
              >
                <Plus className="w-3 h-3" />
                Agregar irrigación
              </button>
            ) : (
              <div className="flex items-center gap-1.5 p-1.5 rounded bg-dark-800 border border-dark-700">
                {/* Temperature spinner */}
                <div className="flex items-center bg-dark-700 rounded border border-dark-600 select-none">
                  <button
                    className="px-1 py-0.5 text-dark-400 hover:text-white transition-colors"
                    onClick={() => setNewStageTemp(prev => Math.max(1, prev - 1))}
                    onMouseDown={() => startHold(-1)}
                    onMouseUp={clearHold}
                    onMouseLeave={clearHold}
                  >
                    <Minus className="w-2.5 h-2.5" />
                  </button>
                  <span className="text-[10px] text-white font-bold w-8 text-center tabular-nums">{newStageTemp}°</span>
                  <button
                    className="px-1 py-0.5 text-dark-400 hover:text-white transition-colors"
                    onClick={() => setNewStageTemp(prev => Math.min(55, prev + 1))}
                    onMouseDown={() => startHold(1)}
                    onMouseUp={clearHold}
                    onMouseLeave={clearHold}
                  >
                    <Plus className="w-2.5 h-2.5" />
                  </button>
                </div>
                <select
                  value={newStageEar}
                  onChange={(e) => setNewStageEar(e.target.value as 'od' | 'oi')}
                  className="bg-dark-700 text-white text-[10px] rounded px-1.5 py-1 border border-dark-600 outline-none"
                >
                  <option value="od">OD</option>
                  <option value="oi">OI</option>
                </select>
                <button
                  onClick={handleAddStage}
                  className="p-1 rounded bg-siev-500 hover:bg-siev-600 text-white transition-colors"
                >
                  <Check className="w-3 h-3" />
                </button>
                <button
                  onClick={() => setShowAddStage(false)}
                  className="p-1 rounded hover:bg-dark-600 text-dark-400 hover:text-white transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            )}
          </div>
          <div className="border-t border-dark-800 my-1" />
        </div>
      )}

      {/* Stimulus Control (Only if test type matches) */}
      {currentTestType && ['calibration_gaze', 'saccades', 'pursuit', 'optokinetic', 'gaze'].includes(currentTestType) && (
        <div className="mb-2">
          <StimulusController testType={currentTestType} appConfig={appConfig} />
        </div>
      )}

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
