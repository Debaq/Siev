import type { ThresholdPoint, Ear, ConductionType } from '../../../types/audiometry'
import { STANDARD_FREQUENCIES } from '../../../types/audiometry'

interface ThresholdTableProps {
  thresholds: ThresholdPoint[]
  onRemove: (frequency: number, ear: Ear, conduction: ConductionType, masked: boolean) => void
}

function formatFreq(f: number): string {
  return f >= 1000 ? `${f / 1000}k` : String(f)
}

export default function ThresholdTable({ thresholds, onRemove }: ThresholdTableProps) {
  const getValue = (
    freq: number,
    ear: Ear,
    conduction: ConductionType,
    masked: boolean
  ): ThresholdPoint | undefined =>
    thresholds.find(
      t =>
        t.frequency === freq &&
        t.ear === ear &&
        t.conduction === conduction &&
        t.masked === masked
    )

  const rows: { ear: Ear; conduction: ConductionType; masked: boolean; label: string; color: string }[] = [
    { ear: 'od', conduction: 'aerea', masked: false, label: 'OD Aérea', color: 'text-red-400' },
    { ear: 'od', conduction: 'osea', masked: false, label: 'OD Ósea', color: 'text-red-300' },
    { ear: 'od', conduction: 'ldl', masked: false, label: 'OD LDL', color: 'text-red-200' },
    { ear: 'oi', conduction: 'aerea', masked: false, label: 'OI Aérea', color: 'text-blue-400' },
    { ear: 'oi', conduction: 'osea', masked: false, label: 'OI Ósea', color: 'text-blue-300' },
    { ear: 'oi', conduction: 'ldl', masked: false, label: 'OI LDL', color: 'text-blue-200' },
  ]

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[10px]">
        <thead>
          <tr className="border-b border-dark-700">
            <th className="text-left py-1 px-1 text-dark-400 font-medium w-20">Serie</th>
            {STANDARD_FREQUENCIES.map(f => (
              <th key={f} className="text-center py-1 px-0.5 text-dark-400 font-medium">
                {formatFreq(f)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(row => (
            <tr key={`${row.ear}-${row.conduction}`} className="border-b border-dark-800/50">
              <td className={`py-1 px-1 font-medium ${row.color}`}>{row.label}</td>
              {STANDARD_FREQUENCIES.map(freq => {
                const point = getValue(freq, row.ear, row.conduction, row.masked)
                return (
                  <td key={freq} className="text-center py-1 px-0.5">
                    {point ? (
                      <button
                        onClick={() => onRemove(freq, row.ear, row.conduction, row.masked)}
                        className={`${row.color} hover:text-white hover:bg-dark-700 rounded px-1 transition-colors ${
                          point.noResponse ? 'line-through opacity-60' : ''
                        }`}
                        title="Click para eliminar"
                      >
                        {point.intensity}
                      </button>
                    ) : (
                      <span className="text-dark-700">—</span>
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
