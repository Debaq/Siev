import { useState, useEffect, useRef, useMemo, memo } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts'
import { Eye, Activity, ChevronLeft, ChevronRight, LucideIcon } from 'lucide-react'

interface EyeDataPanelProps {
  apiUrl: string
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
  dataKeys: [string, string]
  color1: string
  color2: string
  chartData: Array<EyeDataPoint & { index: number }>
  isCalibrated?: boolean
}

const ChartSection = memo(function ChartSection({
  title,
  icon: Icon,
  dataKeys,
  color1,
  color2,
  chartData,
  isCalibrated
}: ChartSectionProps) {
  return (
    <div className="flex flex-col h-full bg-dark-900/50 border border-dark-800 rounded overflow-hidden min-w-0">
      <div className="flex items-center justify-between px-2 py-0.5 border-b border-dark-800 bg-dark-800/30">
        <div className="flex items-center gap-1.5 text-[9px] uppercase font-bold text-dark-400">
          <Icon className="w-2.5 h-2.5" />
          <span>{title}</span>
        </div>
        {title.includes('Horizontal') && isCalibrated && (
          <span className="text-[8px] text-green-400 font-bold bg-green-950/50 px-1 rounded border border-green-900">CAL</span>
        )}
      </div>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.4} />
            <XAxis dataKey="index" hide />
            <YAxis stroke="#475569" tick={{ fontSize: 8 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#020617', border: '1px solid #1e293b', fontSize: '9px', padding: '2px 6px' }}
              itemStyle={{ padding: 0 }}
            />
            <Legend iconType="circle" iconSize={6} wrapperStyle={{ fontSize: '9px', bottom: 0 }} />
            <Line type="monotone" dataKey={dataKeys[0]} stroke={color1} name="OD" dot={false} strokeWidth={1.5} isAnimationActive={false} connectNulls={true} />
            <Line type="monotone" dataKey={dataKeys[1]} stroke={color2} name="OI" dot={false} strokeWidth={1.5} isAnimationActive={false} connectNulls={true} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
})

const MAX_DATA_POINTS = 500
const UPDATE_INTERVAL_MS = 50 // Throttle updates to ~20fps for smooth rendering

function EyeDataPanel({ apiUrl, isCapturing }: EyeDataPanelProps) {
  const [eyeData, setEyeData] = useState<EyeDataPoint[]>([])
  const [isCalibrated, setIsCalibrated] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  const [splitRatio, setSplitRatio] = useState(0.5)
  const [isResizing, setIsResizing] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Throttled update system to prevent flickering
  const pendingDataRef = useRef<EyeDataPoint[]>([])
  const lastUpdateRef = useRef<number>(0)
  const rafIdRef = useRef<number | null>(null)

  useEffect(() => {
    if (!isCapturing) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current)
        rafIdRef.current = null
      }
      pendingDataRef.current = []
      return
    }

    const flushPendingData = () => {
      if (pendingDataRef.current.length === 0) return

      const newPoints = pendingDataRef.current
      pendingDataRef.current = []

      setEyeData((prev) => {
        const combined = [...prev, ...newPoints]
        if (combined.length > MAX_DATA_POINTS) return combined.slice(-MAX_DATA_POINTS)
        return combined
      })
    }

    const scheduleUpdate = () => {
      const now = performance.now()
      const timeSinceLastUpdate = now - lastUpdateRef.current

      if (timeSinceLastUpdate >= UPDATE_INTERVAL_MS) {
        lastUpdateRef.current = now
        flushPendingData()
      } else if (!rafIdRef.current) {
        rafIdRef.current = requestAnimationFrame(() => {
          rafIdRef.current = null
          lastUpdateRef.current = performance.now()
          flushPendingData()
        })
      }
    }

    const eventSource = new EventSource(`${apiUrl}/stream/eye_data`)
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        // Handle both single objects (legacy) and arrays (batch)
        const newPoints: EyeDataPoint[] = (Array.isArray(data) ? data : [data]).map(p => ({
          timestamp: p.timestamp,
          leftX: p.left_eye?.[0] ?? null,
          leftY: p.left_eye?.[1] ?? null,
          rightX: p.right_eye?.[0] ?? null,
          rightY: p.right_eye?.[1] ?? null,
        }))

        // Accumulate data and schedule throttled update
        pendingDataRef.current.push(...newPoints)
        scheduleUpdate()

        // Use the last point's calibration status (this is lightweight, no throttle needed)
        const lastRaw = Array.isArray(data) ? data[data.length - 1] : data
        if (lastRaw) setIsCalibrated(lastRaw.is_calibrated ?? false)

      } catch (error) { console.error(error) }
    }

    return () => {
      eventSource.close()
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current)
      }
    }
  }, [apiUrl, isCapturing])

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

  const chartData = useMemo(
    () => eyeData.map((point, index) => ({ index, ...point })),
    [eyeData]
  )

  return (
    <div ref={containerRef} className="flex w-full h-full overflow-hidden select-none bg-dark-950/20 p-0.5">
      
      {/* Left Chart */}
      {splitRatio > 0 && (
        <div style={{ width: `${splitRatio * 100}%` }} className="h-full pr-0.5">
          <ChartSection
            title="Posición X (Horizontal)"
            icon={Eye}
            dataKeys={['leftX', 'rightX']}
            color1="#f43f5e"
            color2="#0ea5e9"
            chartData={chartData}
            isCalibrated={isCalibrated}
          />
        </div>
      )}

      {/* Splitter Handle - Sleek version */}
      <div 
        className={`w-1 group relative flex items-center justify-center transition-colors cursor-col-resize z-30 ${isResizing ? 'bg-siev-500' : 'bg-dark-800 hover:bg-dark-600'}`}
        onMouseDown={() => setIsResizing(true)}
      >
        {/* Hover arrows - Integrated into the bar style */}
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

      {/* Right Chart */}
      {splitRatio < 1 && (
        <div style={{ flex: 1 }} className="h-full pl-0.5">
          <ChartSection
            title="Posición Y (Vertical)"
            icon={Activity}
            dataKeys={['leftY', 'rightY']}
            color1="#f43f5e"
            color2="#0ea5e9"
            chartData={chartData}
            isCalibrated={isCalibrated}
          />
        </div>
      )}

    </div>
  )
}

export default EyeDataPanel
