import { CaloricProtocolTiming } from '../types/config'
import { CaloricTimerPhase } from '../hooks/useCaloricTimer'

interface CaloricTimelineProps {
  protocolName: string
  stageLabel: string
  timing: CaloricProtocolTiming
  elapsedSeconds: number
  currentPhase: CaloricTimerPhase
  progress: number
  isRunning: boolean
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

const phaseBadgeStyles: Record<CaloricTimerPhase['key'], string> = {
  delay: 'bg-dark-700 text-dark-400',
  irrigation: 'bg-orange-500/20 text-orange-400',
  recording: 'bg-dark-700 text-dark-300',
  torok: 'bg-amber-500/20 text-amber-400',
  ofi: 'bg-green-500/20 text-green-400',
}

export default function CaloricTimeline({
  protocolName,
  stageLabel,
  timing,
  elapsedSeconds,
  currentPhase,
  progress,
  isRunning,
}: CaloricTimelineProps) {
  const total = timing.delay + timing.total_duration
  if (total <= 0) return null

  const pct = (v: number) => (v / total) * 100

  // Segment positions as percentages of total
  const delayPct = pct(timing.delay)

  const irrigationDur = timing.irrigation_duration ?? 0
  const irrigationStartPct = pct(timing.delay)
  const irrigationWidthPct = pct(irrigationDur)

  const torokStartPct = pct(timing.delay + timing.torok.start_time)
  const torokWidthPct = pct(timing.torok.duration)

  const ofiStartPct = pct(timing.delay + timing.ofi.start_time)
  const ofiWidthPct = pct(timing.ofi.duration)

  const progressPct = progress * 100

  return (
    <div className="h-[56px] bg-dark-900 border-t border-b border-dark-800 px-3 py-1 flex flex-col justify-center select-none shrink-0">
      {/* Header row */}
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-dark-400 truncate">
          {protocolName} <span className="text-dark-500">•</span> {stageLabel}
        </span>
        <div className="flex items-center gap-2">
          <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${phaseBadgeStyles[currentPhase.key]}`}>
            {currentPhase.name}
          </span>
          <span className="text-[10px] text-dark-500 tabular-nums">
            {formatTime(elapsedSeconds)} / {formatTime(total)}
          </span>
        </div>
      </div>

      {/* Triangle indicator - above the bar */}
      <div className="relative h-3 shrink-0">
        {isRunning && (
          <div
            className="absolute bottom-0 transition-[left] duration-100 ease-linear"
            style={{ left: `${progressPct}%` }}
          >
            <div
              className="absolute bottom-0 -translate-x-1/2"
              style={{
                width: 0,
                height: 0,
                borderLeft: '6px solid transparent',
                borderRight: '6px solid transparent',
                borderTop: '8px solid white',
              }}
            />
          </div>
        )}
      </div>

      {/* Timeline bar */}
      <div className="relative h-3 bg-dark-800 rounded-sm overflow-hidden">
        {/* Delay segment */}
        {timing.delay > 0 && (
          <div
            className="absolute inset-y-0 bg-dark-600/60 border-r border-dark-500"
            style={{ left: 0, width: `${delayPct}%` }}
          />
        )}

        {/* Irrigation segment */}
        {irrigationDur > 0 && (
          <div
            className="absolute inset-y-0 bg-orange-500/25 border-x border-orange-500/40"
            style={{ left: `${irrigationStartPct}%`, width: `${irrigationWidthPct}%` }}
          />
        )}

        {/* Török segment */}
        {timing.torok.duration > 0 && (
          <div
            className="absolute inset-y-0 bg-amber-500/20 border-x border-amber-500/40"
            style={{ left: `${torokStartPct}%`, width: `${torokWidthPct}%` }}
          />
        )}

        {/* OFI segment */}
        {timing.ofi.duration > 0 && (
          <div
            className="absolute inset-y-0 bg-green-500/20 border-x border-green-500/40"
            style={{ left: `${ofiStartPct}%`, width: `${ofiWidthPct}%` }}
          />
        )}

        {/* Progress fill */}
        <div
          className="absolute inset-y-0 left-0 bg-white/10 transition-[width] duration-100 ease-linear"
          style={{ width: `${progressPct}%` }}
        />

        {/* Vertical line at progress position */}
        {isRunning && (
          <div
            className="absolute top-0 bottom-0 w-px bg-white transition-[left] duration-100 ease-linear -translate-x-1/2"
            style={{ left: `${progressPct}%` }}
          />
        )}
      </div>
    </div>
  )
}
