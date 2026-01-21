import { useState, useCallback } from 'react'
import {
  Play, Square, Circle, Crosshair,
  Cpu, Lightbulb, LightbulbOff,
  Sun, Contrast, Activity, Eye
} from 'lucide-react'

interface ControlPanelProps {
  isCapturing: boolean
  isRecording: boolean
  hardwareStatus: 'offline' | 'online' | 'error'
  onStartCapture: () => void
  onStopCapture: () => void
  onStartRecording: () => void
  onStopRecording: () => void
  onCalibrate: () => void
  apiUrl: string
}

function ControlPanel({
  isCapturing,
  isRecording,
  hardwareStatus,
  onStartCapture,
  onStopCapture,
  onStartRecording,
  onStopRecording,
  onCalibrate,
  apiUrl,
}: ControlPanelProps) {
  const [yoloEnabled, setYoloEnabled] = useState(true)
  const [showDebug, setShowDebug] = useState(false)
  const [brightness, setBrightness] = useState(-21)
  const [contrast, setContrast] = useState(50)
  const [threshold, setThreshold] = useState<[number, number]>([0, 0])
  const [erode, setErode] = useState<[number, number]>([0, 0])
  const [noseWidth, setNoseWidth] = useState(0.25)
  const [eyeHeight, setEyeHeight] = useState(0.25)

  const updateVideoConfig = useCallback(async (overrides: any = {}) => {
    try {
      const config = {
        brightness,
        contrast,
        threshold,
        erode,
        nose_width: noseWidth,
        eye_height: eyeHeight,
        use_yolo: yoloEnabled,
        show_debug: showDebug,
        ...overrides
      }

      await fetch(`${apiUrl}/video/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
    } catch (error) {
      console.error('Error updating config:', error)
    }
  }, [apiUrl, brightness, contrast, threshold, erode, noseWidth, eyeHeight, yoloEnabled, showDebug])

  const handleBrightnessChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value)
    setBrightness(val)
    updateVideoConfig({ brightness: val })
  }

  const handleContrastChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value)
    setContrast(val)
    updateVideoConfig({ contrast: val })
  }

  const handleThresholdChange = (eye: 'right' | 'left', val: number) => {
    const newThreshold: [number, number] = eye === 'right' ? [val, threshold[1]] : [threshold[0], val]
    setThreshold(newThreshold)
    updateVideoConfig({ threshold: newThreshold })
  }

  const handleErodeChange = (eye: 'right' | 'left', val: number) => {
    const newErode: [number, number] = eye === 'right' ? [val, erode[1]] : [erode[0], val]
    setErode(newErode)
    updateVideoConfig({ erode: newErode })
  }

  const handleNoseWidthChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value)
    setNoseWidth(val)
    updateVideoConfig({ nose_width: val })
  }

  const handleEyeHeightChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value)
    setEyeHeight(val)
    updateVideoConfig({ eye_height: val })
  }

  const handleToggleYolo = async () => {
    const newVal = !yoloEnabled
    setYoloEnabled(newVal)
    updateVideoConfig({ use_yolo: newVal })
  }

  const handleToggleDebug = async () => {
    const newVal = !showDebug
    setShowDebug(newVal)
    updateVideoConfig({ show_debug: newVal })
  }

  const handleLed = async (led: string, action: 'on' | 'off') => {
    try {
      await fetch(`${apiUrl}/hardware/led/${led}/${action}`, { method: 'POST' })
    } catch (error) { console.error(error) }
  }

  const SectionTitle = ({ icon: Icon, title }: { icon: any, title: string }) => (
    <div className="flex items-center gap-1.5 text-[10px] uppercase font-bold text-dark-400 mt-4 mb-2 pl-1">
      <Icon className="w-3 h-3" />
      <span>{title}</span>
    </div>
  )

  return (
    <div className="flex flex-col h-full">
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
          onClick={isRecording ? onStopRecording : onStartRecording}
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
              value={erode[1]}
              onChange={(e) => handleErodeChange('left', Number(e.target.value))}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="flex justify-between text-[10px] text-dark-400 mb-1">
              <span>Ancho Nariz</span>
              <span>{noseWidth.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.05" max="0.5" step="0.01"
              value={noseWidth}
              onChange={handleNoseWidthChange}
            />
          </div>
          <div>
            <div className="flex justify-between text-[10px] text-dark-400 mb-1">
              <span>Altura Ojo</span>
              <span>{eyeHeight.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.05" max="0.5" step="0.01"
              value={eyeHeight}
              onChange={handleEyeHeightChange}
            />
          </div>
        </div>
      </div>

      {/* Detection */}
      <SectionTitle icon={Cpu} title="Procesamiento" />
      <div className="px-1 space-y-2">
        <button
          className={`w-full btn ${yoloEnabled ? 'btn-primary' : 'btn-secondary'} justify-between px-3`}
          onClick={handleToggleYolo}
        >
          <span className="text-[10px]">Detección IA (YOLO)</span>
          <div className={`w-2 h-2 rounded-full ${yoloEnabled ? 'bg-white' : 'bg-dark-500'}`} />
        </button>

        <button
          className={`w-full btn ${showDebug ? 'btn-success' : 'btn-secondary'} justify-between px-3`}
          onClick={handleToggleDebug}
        >
          <div className="flex items-center gap-1">
            <Eye className="w-3 h-3" />
            <span className="text-[10px]">Modo Debug</span>
          </div>
          <div className={`w-2 h-2 rounded-full ${showDebug ? 'bg-white' : 'bg-dark-500'}`} />
        </button>
        {showDebug && (
          <div className="text-[9px] text-yellow-400 bg-yellow-500/10 rounded p-1.5 border border-yellow-500/30">
            Muestra máscaras de umbral y ROIs para ajustar parámetros
          </div>
        )}
      </div>

      {/* Hardware */}
      <SectionTitle icon={Activity} title="Hardware" />
      <div className="px-1 space-y-2">
        <div className="grid grid-cols-2 gap-2">
           {/* Left LED */}
           <div className="bg-dark-800 rounded p-1.5 flex flex-col gap-1">
              <span className="text-[9px] text-center text-dark-400">LED IZQ</span>
              <div className="flex gap-1">
                <button 
                  className="btn btn-secondary flex-1 p-0 h-6" 
                  onClick={() => handleLed('left', 'on')}
                  disabled={hardwareStatus !== 'online'}
                >
                  <Lightbulb className="w-3 h-3 text-yellow-400" />
                </button>
                <button 
                  className="btn btn-secondary flex-1 p-0 h-6"
                  onClick={() => handleLed('left', 'off')}
                  disabled={hardwareStatus !== 'online'}
                >
                  <LightbulbOff className="w-3 h-3" />
                </button>
              </div>
           </div>
           
           {/* Right LED */}
           <div className="bg-dark-800 rounded p-1.5 flex flex-col gap-1">
              <span className="text-[9px] text-center text-dark-400">LED DER</span>
              <div className="flex gap-1">
                <button 
                  className="btn btn-secondary flex-1 p-0 h-6" 
                  onClick={() => handleLed('right', 'on')}
                  disabled={hardwareStatus !== 'online'}
                >
                  <Lightbulb className="w-3 h-3 text-yellow-400" />
                </button>
                <button 
                  className="btn btn-secondary flex-1 p-0 h-6"
                  onClick={() => handleLed('right', 'off')}
                  disabled={hardwareStatus !== 'online'}
                >
                  <LightbulbOff className="w-3 h-3" />
                </button>
              </div>
           </div>
        </div>
        <button
            className="btn btn-secondary w-full text-[10px] h-6"
            onClick={() => handleLed('all', 'off')}
            disabled={hardwareStatus !== 'online'}
          >
            APAGAR TODOS
          </button>
      </div>
    </div>
  )
}

export default ControlPanel