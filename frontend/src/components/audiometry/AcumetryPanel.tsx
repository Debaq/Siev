import type { AcumetryData, RinneValue, WeberOdValue, WeberOiValue } from '../../types/audiometry'

interface AcumetryPanelProps {
  acumetry: AcumetryData
  onUpdate: (field: keyof AcumetryData, value: string | undefined) => void
}

// Ciclos de valores para cada tipo de botón
const RINNE_CYCLE: (RinneValue | undefined)[] = [undefined, '+', '-', 'ne', 'f-']
const WEBER_OD_CYCLE: (WeberOdValue | undefined)[] = [undefined, '-', '<']
const WEBER_OI_CYCLE: (WeberOiValue | undefined)[] = [undefined, '-', '>']

function nextInCycle<T>(cycle: T[], current: T): T {
  const idx = cycle.indexOf(current)
  return cycle[(idx + 1) % cycle.length]
}

function displayRinne(val: RinneValue | undefined): string {
  if (val === undefined) return 'R'
  if (val === 'ne') return 'NE'
  if (val === 'f-') return 'F−'
  if (val === '-') return '−'
  return val
}

function displayWeber(val: WeberOdValue | WeberOiValue | undefined): string {
  if (val === undefined) return 'W'
  if (val === '-') return '−'
  return val
}

export default function AcumetryPanel({ acumetry, onUpdate }: AcumetryPanelProps) {
  const freqs = [500, 1000] as const

  const fields = (freq: 500 | 1000) => ({
    weberOd: `weber_od_${freq}` as keyof AcumetryData,
    rinneOd: `rinne_od_${freq}` as keyof AcumetryData,
    rinneOi: `rinne_oi_${freq}` as keyof AcumetryData,
    weberOi: `weber_oi_${freq}` as keyof AcumetryData,
  })

  const isDefault = (freq: 500 | 1000) => {
    const f = fields(freq)
    return !acumetry[f.weberOd] && !acumetry[f.rinneOd] && !acumetry[f.rinneOi] && !acumetry[f.weberOi]
  }

  return (
    <div className="flex items-center justify-center gap-6 px-2 py-2">
      {freqs.map(freq => {
        const f = fields(freq)
        const allDefault = isDefault(freq)
        return (
          <div key={freq} className="flex items-center gap-0.5">
            {/* Weber OD — corchetes rojos */}
            <button
              onClick={() => onUpdate(f.weberOd, nextInCycle(WEBER_OD_CYCLE, acumetry[f.weberOd] as WeberOdValue | undefined))}
              className={`min-w-[22px] h-[20px] rounded-sm text-[10px] font-bold transition-colors border ${
                acumetry[f.weberOd]
                  ? 'bg-red-500/25 text-red-300 border-red-500/40'
                  : 'bg-dark-800 text-red-400/50 border-dark-700 hover:border-red-500/30'
              }`}
              title="Weber OD"
            >
              {displayWeber(acumetry[f.weberOd] as WeberOdValue | undefined)}
            </button>

            {/* Rinne OD — paréntesis rojos */}
            <button
              onClick={() => onUpdate(f.rinneOd, nextInCycle(RINNE_CYCLE, acumetry[f.rinneOd] as RinneValue | undefined))}
              className={`min-w-[22px] h-[20px] rounded-full text-[10px] font-bold transition-colors border ${
                acumetry[f.rinneOd]
                  ? 'bg-red-500/25 text-red-300 border-red-500/40'
                  : 'bg-dark-800 text-red-400/50 border-dark-700 hover:border-red-500/30'
              }`}
              title="Rinne OD"
            >
              {displayRinne(acumetry[f.rinneOd] as RinneValue | undefined)}
            </button>

            {/* Frecuencia */}
            <span className={`mx-1 text-[11px] font-bold select-none ${
              allDefault ? 'text-dark-600 line-through' : 'text-dark-200'
            }`}>
              {freq}
            </span>

            {/* Rinne OI — paréntesis azules */}
            <button
              onClick={() => onUpdate(f.rinneOi, nextInCycle(RINNE_CYCLE, acumetry[f.rinneOi] as RinneValue | undefined))}
              className={`min-w-[22px] h-[20px] rounded-full text-[10px] font-bold transition-colors border ${
                acumetry[f.rinneOi]
                  ? 'bg-blue-500/25 text-blue-300 border-blue-500/40'
                  : 'bg-dark-800 text-blue-400/50 border-dark-700 hover:border-blue-500/30'
              }`}
              title="Rinne OI"
            >
              {displayRinne(acumetry[f.rinneOi] as RinneValue | undefined)}
            </button>

            {/* Weber OI — corchetes azules */}
            <button
              onClick={() => onUpdate(f.weberOi, nextInCycle(WEBER_OI_CYCLE, acumetry[f.weberOi] as WeberOiValue | undefined))}
              className={`min-w-[22px] h-[20px] rounded-sm text-[10px] font-bold transition-colors border ${
                acumetry[f.weberOi]
                  ? 'bg-blue-500/25 text-blue-300 border-blue-500/40'
                  : 'bg-dark-800 text-blue-400/50 border-dark-700 hover:border-blue-500/30'
              }`}
              title="Weber OI"
            >
              {displayWeber(acumetry[f.weberOi] as WeberOiValue | undefined)}
            </button>
          </div>
        )
      })}
    </div>
  )
}
