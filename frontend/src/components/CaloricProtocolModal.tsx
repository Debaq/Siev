import { X, Thermometer, Check, Clock } from 'lucide-react'
import { CaloricProtocol, CaloricProtocolTiming } from '../types/config'

function formatSeconds(s: number): string {
  if (s >= 60) {
    const m = Math.floor(s / 60)
    const rest = s % 60
    return rest > 0 ? `${m}m ${rest}s` : `${m}m`
  }
  return `${s}s`
}

function TimingBar({ timing }: { timing: CaloricProtocolTiming }) {
  const total = timing.total_duration
  if (total <= 0) return null

  // Build segments: delay, irrigation, torok, ofi
  const segments: { start: number; end: number; label: string; color: string }[] = []

  if (timing.delay > 0) {
    segments.push({ start: 0, end: timing.delay, label: 'Espera', color: 'bg-dark-600' })
  }

  if ((timing.irrigation_duration ?? 0) > 0) {
    segments.push({ start: 0, end: timing.irrigation_duration, label: 'Irrigación', color: 'bg-orange-500' })
  }

  segments.push({
    start: timing.torok.start_time,
    end: timing.torok.start_time + timing.torok.duration,
    label: 'Török',
    color: 'bg-sky-500',
  })

  segments.push({
    start: timing.ofi.start_time,
    end: timing.ofi.start_time + timing.ofi.duration,
    label: 'OFI',
    color: 'bg-amber-500',
  })

  return (
    <div className="mt-auto">
      <div className="flex items-center gap-1.5 mb-1">
        <Clock className="w-2.5 h-2.5 text-dark-500" />
        <span className="text-[9px] text-dark-500 font-medium">{formatSeconds(total)} por prueba</span>
      </div>
      {/* Bar */}
      <div className="relative h-2 rounded-full bg-dark-700 overflow-hidden">
        {segments.map((seg, i) => {
          const left = (seg.start / total) * 100
          const width = ((seg.end - seg.start) / total) * 100
          return (
            <div
              key={i}
              className={`absolute top-0 h-full rounded-full ${seg.color}`}
              style={{ left: `${left}%`, width: `${width}%` }}
              title={`${seg.label}: ${formatSeconds(seg.end - seg.start)}`}
            />
          )
        })}
      </div>
      {/* Legend */}
      <div className="flex items-center gap-3 mt-1">
        <div className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-orange-500" />
          <span className="text-[8px] text-dark-500">Irrigación</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-sky-500" />
          <span className="text-[8px] text-dark-500">Török</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
          <span className="text-[8px] text-dark-500">OFI</span>
        </div>
        {timing.rest_time > 0 && (
          <span className="text-[8px] text-dark-500 ml-auto">Reposo: {formatSeconds(timing.rest_time)}</span>
        )}
      </div>
    </div>
  )
}

interface CaloricProtocolModalProps {
  protocols: CaloricProtocol[]
  onSelect: (protocol: CaloricProtocol) => void
  onCancel: () => void
}

function CaloricProtocolModal({ protocols, onSelect, onCancel }: CaloricProtocolModalProps) {
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-8">
      <div className="bg-dark-900 border border-dark-700 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-dark-700">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-500/10">
              <Thermometer className="w-6 h-6 text-red-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Seleccionar Protocolo Calórico</h2>
              <p className="text-sm text-dark-400">Elija el protocolo de irrigaciones a realizar</p>
            </div>
          </div>
          <button
            onClick={onCancel}
            className="p-2 hover:bg-dark-800 rounded-lg text-dark-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Protocol Cards */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {protocols.map((proto) => (
              <button
                key={proto.id}
                onClick={() => onSelect(proto)}
                className="flex flex-col p-5 rounded-xl border border-dark-700 bg-dark-800/50 hover:bg-dark-800 hover:border-red-500/40 transition-all group text-left"
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-bold text-white group-hover:text-red-400 transition-colors">
                    {proto.name}
                  </h3>
                  {proto.is_base && (
                    <span className="text-[8px] font-bold px-2 py-0.5 rounded-full bg-siev-500/20 text-siev-400 uppercase">
                      Base
                    </span>
                  )}
                </div>

                {proto.comment && (
                  <p className="text-xs text-dark-400 mb-3">{proto.comment}</p>
                )}

                {/* Irrigations list */}
                <div className="space-y-1.5 mb-3">
                  {proto.irrigations.map((irr, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <span className="w-4 h-4 rounded-full bg-dark-700 flex items-center justify-center text-[9px] font-bold text-dark-300">
                        {i + 1}
                      </span>
                      <span className={`font-medium ${irr.temperature >= 40 ? 'text-red-400' : 'text-blue-400'}`}>
                        {irr.temperature}°C
                      </span>
                      <span className="text-dark-400">{irr.ear.toUpperCase()}</span>
                      <span className="text-dark-500">—</span>
                      <span className="text-dark-400">{irr.label}</span>
                    </div>
                  ))}
                </div>

                {/* Timing timeline */}
                {proto.timing && <TimingBar timing={proto.timing} />}

                <div className="flex items-center justify-between mt-3 pt-3 border-t border-dark-700">
                  <span className="text-[10px] text-dark-500">
                    {proto.irrigations.length} irrigaciones
                  </span>
                  <span className="text-[10px] text-dark-500 group-hover:text-red-400 flex items-center gap-1 transition-colors">
                    <Check className="w-3 h-3" />
                    Seleccionar
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default CaloricProtocolModal
