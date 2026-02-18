import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import uPlot from 'uplot'
import { Eye, Activity, ChevronLeft, ChevronRight, LucideIcon } from 'lucide-react'
import { invoke } from '@tauri-apps/api/core'
import { useWebSocket } from '../contexts/WebSocketContext'
import UPlotChart from './charts/UPlotChart'

interface EyeDataPanelProps {
  isCapturing: boolean
}

interface EyeDataPoint {
  timestamp: number
  leftX: number | null
  leftY: number | null
  rightX: number | null
  rightY: number | null
}

interface ChartSectionProps {
  title: string
  icon: LucideIcon
  dataKeys: [keyof EyeDataPoint, keyof EyeDataPoint]
  color1: string
  color2: string
  data: EyeDataPoint[]
  isCalibrated?: boolean
  onResetCalibration?: () => void
  useRustFilter: boolean
  onToggleFilter: () => void
  overlayMessage?: string | null
}

// 5 minutos a 30fps = 9000 puntos, con margen
const MAX_DATA_POINTS = 10000

// Downsampling LTTB (Largest Triangle Three Buckets) para visualización
function downsampleLTTB(data: number[], threshold: number): number[] {
  if (data.length <= threshold) return data

  const sampled: number[] = []
  const bucketSize = (data.length - 2) / (threshold - 2)

  sampled.push(data[0])

  for (let i = 0; i < threshold - 2; i++) {
    const avgRangeStart = Math.floor((i + 1) * bucketSize) + 1
    const avgRangeEnd = Math.min(Math.floor((i + 2) * bucketSize) + 1, data.length)

    let avgY = 0
    for (let j = avgRangeStart; j < avgRangeEnd; j++) {
      avgY += data[j] ?? 0
    }
    avgY /= (avgRangeEnd - avgRangeStart)

    const rangeStart = Math.floor(i * bucketSize) + 1
    const rangeEnd = Math.floor((i + 1) * bucketSize) + 1

    const pointAX = sampled.length - 1
    const pointAY = sampled[sampled.length - 1]

    let maxArea = -1
    let maxAreaPoint = rangeStart

    for (let j = rangeStart; j < rangeEnd; j++) {
      const area = Math.abs(
        (pointAX - (threshold - 2)) * ((data[j] ?? 0) - pointAY) -
        (pointAX - j) * (avgY - pointAY)
      ) * 0.5

      if (area > maxArea) {
        maxArea = area
        maxAreaPoint = j
      }
    }

    sampled.push(data[maxAreaPoint])
  }

  sampled.push(data[data.length - 1])
  return sampled
}

function ChartSection({
  title,
  icon: Icon,
  dataKeys,
  color1,
  color2,
  data,
  isCalibrated,
  onResetCalibration,
  useRustFilter,
  onToggleFilter,
  overlayMessage
}: ChartSectionProps) {
  const displayThreshold = 1000

  const uplotData = useMemo<uPlot.AlignedData>(() => {
    if (data.length === 0) return [[], [], []] as unknown as uPlot.AlignedData

    const series1Raw = data.map(d => (d[dataKeys[0]] as number | null) ?? 0)
    const series2Raw = data.map(d => (d[dataKeys[1]] as number | null) ?? 0)

    const series1 = data.length > displayThreshold
      ? downsampleLTTB(series1Raw, displayThreshold)
      : series1Raw
    const series2 = data.length > displayThreshold
      ? downsampleLTTB(series2Raw, displayThreshold)
      : series2Raw

    // Timestamps como índices (equiespaciados)
    const timestamps = Array.from({ length: series1.length }, (_, i) => i)

    return [timestamps, series1, series2]
  }, [data, dataKeys])

  const options = useMemo((): Omit<uPlot.Options, 'width' | 'height'> => ({
    cursor: {
      drag: { x: true, y: false, setScale: true },
      show: true,
    },
    select: { show: false, left: 0, top: 0, width: 0, height: 0 },
    legend: { show: false },
    padding: [8, 8, 0, 0],
    axes: [
      {
        show: false, // X axis hidden (index-based)
      },
      {
        stroke: '#475569',
        grid: { stroke: '#1e293b', dash: [2, 4] },
        ticks: { show: false },
        font: '8px system-ui',
        size: 35,
        gap: 2,
      },
    ],
    scales: {
      x: { auto: true },
      y: { auto: true },
    },
    series: [
      {}, // x-axis timestamps
      {
        label: 'OD',
        stroke: color1,
        width: 1.5,
        points: { show: false },
      },
      {
        label: 'OI',
        stroke: color2,
        width: 1.5,
        points: { show: false },
      },
    ],
  }), [color1, color2])

  return (
    <div className="flex flex-col h-full bg-dark-900/50 border border-dark-800 rounded overflow-hidden min-w-0">
      <div className="flex items-center justify-between px-2 py-0.5 border-b border-dark-800 bg-dark-800/30">
        <div className="flex items-center gap-1.5 text-[9px] uppercase font-bold text-dark-400">
          <Icon className="w-2.5 h-2.5" />
          <span>{title}</span>
          {data.length > 0 && (
            <span className="text-dark-500 font-normal">({data.length} pts)</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {title.includes('Horizontal') && (
            <button
              onClick={onToggleFilter}
              className={`text-[8px] font-bold px-1 rounded border transition-colors ${useRustFilter ? 'text-siev-400 bg-siev-950/50 border-siev-900' : 'text-dark-400 bg-dark-800 border-dark-700'}`}
              title={useRustFilter ? "Usando Filtro Rust (Optimizado)" : "Usando Datos Originales (Backend)"}
            >
              {useRustFilter ? 'FILTRO: ON' : 'FILTRO: OFF'}
            </button>
          )}
          {title.includes('Horizontal') && isCalibrated && useRustFilter && (
            <span className="text-[8px] text-green-400 font-bold bg-green-950/50 px-1 rounded border border-green-900">CAL</span>
          )}
          {title.includes('Horizontal') && useRustFilter && (
            <button
              onClick={onResetCalibration}
              className="text-[8px] text-dark-400 hover:text-white bg-dark-800 hover:bg-dark-700 px-1 rounded border border-dark-700 transition-colors"
              title="Reiniciar Calibración"
            >
              RESET
            </button>
          )}
        </div>
      </div>
      <div className="flex-1 min-h-0 relative">
        <UPlotChart
          options={options}
          data={uplotData}
        />
        {overlayMessage && (
          <div className="absolute inset-0 flex items-center justify-center bg-dark-900/80 z-10">
            <div className="flex flex-col items-center gap-2">
              <div className="w-4 h-4 border-2 border-siev-400 border-t-transparent rounded-full animate-spin" />
              <span className="text-[11px] text-siev-300 font-medium">{overlayMessage}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const INITIAL_DELAY_MS = 3000

function EyeDataPanel({ isCapturing }: EyeDataPanelProps) {
  const { addListener, removeListener } = useWebSocket()
  const [history, setHistory] = useState<EyeDataPoint[]>([])
  const [isCalibrated, setIsCalibrated] = useState(false)
  const isCalibratedRef = useRef(false)
  const [useRustFilter, setUseRustFilter] = useState(true)
  const [initializing, setInitializing] = useState(false)

  const [splitRatio, setSplitRatio] = useState(0.5)
  const [isResizing, setIsResizing] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Keep ref in sync
  useEffect(() => {
    isCalibratedRef.current = isCalibrated
  }, [isCalibrated])

  // Initial delay when capture starts — gives time for camera detection
  useEffect(() => {
    if (isCapturing) {
      setInitializing(true)
      const timer = setTimeout(() => setInitializing(false), INITIAL_DELAY_MS)
      return () => clearTimeout(timer)
    } else {
      setInitializing(false)
    }
  }, [isCapturing])

  // Track initializing state with a ref so the WS handler always has the current value
  const initializingRef = useRef(false)
  useEffect(() => {
    initializingRef.current = initializing
  }, [initializing])

  // Handle new eye data from WebSocket with batching
  useEffect(() => {
    if (!isCapturing) return

    let pendingPoints: EyeDataPoint[] = []

    // Flush cada 100ms (~10 FPS para UI)
    const flushInterval = setInterval(() => {
      if (pendingPoints.length > 0) {
        setHistory(prev => {
          const combined = [...prev, ...pendingPoints]
          return combined.length > MAX_DATA_POINTS
            ? combined.slice(-MAX_DATA_POINTS)
            : combined
        })
        pendingPoints = []
      }
    }, 100)

    const handleData = (data: any) => {
      // Ignorar datos durante el delay inicial (detección de cámara)
      if (initializingRef.current) return

      const wsEyeData = data as {
        left: number[] | null
        right: number[] | null
        timestamp: number
        is_calibrated: boolean
      }

      // Detectar fin de calibración: transición a calibrado → limpiar datos
      if (wsEyeData.is_calibrated && !isCalibratedRef.current) {
        setHistory([])
        pendingPoints = []
      }

      if (wsEyeData.is_calibrated !== isCalibratedRef.current) {
        setIsCalibrated(wsEyeData.is_calibrated)
      }

      const newPoint: EyeDataPoint = {
        timestamp: wsEyeData.timestamp,
        leftX: wsEyeData.left?.[0] ?? null,
        leftY: wsEyeData.left?.[1] ?? null,
        rightX: wsEyeData.right?.[0] ?? null,
        rightY: wsEyeData.right?.[1] ?? null
      }

      pendingPoints.push(newPoint)
    }

    addListener('eye_data', handleData)

    return () => {
      removeListener('eye_data', handleData)
      clearInterval(flushInterval)
    }
  }, [isCapturing, addListener, removeListener])

  // Clear history when stopping
  useEffect(() => {
    if (!isCapturing) setHistory([])
  }, [isCapturing])

  const handleResetCalibration = useCallback(() => {
    invoke('reset_calibration').catch(console.error)
  }, [])

  const toggleRustFilter = useCallback(() => {
    const newValue = !useRustFilter
    setUseRustFilter(newValue)
    invoke('set_filtering_enabled', { enabled: newValue }).catch(console.error)
  }, [useRustFilter])

  // Splitter resize handling
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing || !containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      const relativeX = e.clientX - rect.left
      let newRatio = relativeX / rect.width
      if (newRatio < 0.05) newRatio = 0
      if (newRatio > 0.95) newRatio = 1
      setSplitRatio(Math.max(0, Math.min(1, newRatio)))
    }

    const handleMouseUp = () => {
      setIsResizing(false)
      document.body.style.cursor = 'default'
    }

    if (isResizing) {
      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'col-resize'
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizing])

  return (
    <div ref={containerRef} className="flex w-full h-full overflow-hidden select-none bg-dark-950/20 p-0.5">
      {/* Left Chart - Horizontal */}
      {splitRatio > 0 && (
        <div style={{ width: `${splitRatio * 100}%` }} className="h-full pr-0.5">
          <ChartSection
            title="Posición X (Horizontal)"
            icon={Eye}
            dataKeys={['rightX', 'leftX']}
            color1="#f43f5e"
            color2="#0ea5e9"
            data={history}
            isCalibrated={isCalibrated}
            onResetCalibration={handleResetCalibration}
            useRustFilter={useRustFilter}
            onToggleFilter={toggleRustFilter}
            overlayMessage={initializing ? 'Inicializando cámara...' : null}
          />
        </div>
      )}

      {/* Splitter Handle */}
      <div
        className={`w-1 group relative flex items-center justify-center transition-colors cursor-col-resize z-30 ${isResizing ? 'bg-siev-500' : 'bg-dark-800 hover:bg-dark-600'}`}
        onMouseDown={() => setIsResizing(true)}
      >
        <div className="absolute inset-y-0 -left-2 -right-2 flex flex-col items-center justify-center gap-8 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="flex flex-col gap-1 pointer-events-auto">
            <button
              className="w-4 h-6 flex items-center justify-center bg-dark-800 hover:bg-siev-600 border border-dark-700 rounded-sm text-dark-300 hover:text-white transition-colors"
              onClick={(e) => { e.stopPropagation(); setSplitRatio(splitRatio === 1 ? 0.5 : 1) }}
            >
              <ChevronRight className={`w-3 h-3 ${splitRatio === 1 ? 'rotate-180' : ''}`} />
            </button>
            <button
              className="w-4 h-6 flex items-center justify-center bg-dark-800 hover:bg-siev-600 border border-dark-700 rounded-sm text-dark-300 hover:text-white transition-colors"
              onClick={(e) => { e.stopPropagation(); setSplitRatio(splitRatio === 0 ? 0.5 : 0) }}
            >
              <ChevronLeft className={`w-3 h-3 ${splitRatio === 0 ? 'rotate-180' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {/* Right Chart - Vertical */}
      {splitRatio < 1 && (
        <div style={{ flex: 1 }} className="h-full pl-0.5">
          <ChartSection
            title="Posición Y (Vertical)"
            icon={Activity}
            dataKeys={['rightY', 'leftY']}
            color1="#f43f5e"
            color2="#0ea5e9"
            data={history}
            isCalibrated={isCalibrated}
            onResetCalibration={handleResetCalibration}
            useRustFilter={useRustFilter}
            onToggleFilter={toggleRustFilter}
            overlayMessage={initializing ? 'Inicializando cámara...' : null}
          />
        </div>
      )}
    </div>
  )
}

export default EyeDataPanel
