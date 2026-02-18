import type { HearingClassificationResult } from '../../../types/audiometry'
import { gradeLabel, typeLabel } from '../../../types/audiometry'

interface HearingClassificationProps {
  classifications: HearingClassificationResult[]
}

function getGradeColor(grade: string): string {
  switch (grade) {
    case 'normal':
      return 'text-green-400'
    case 'leve':
      return 'text-yellow-400'
    case 'moderada':
      return 'text-orange-400'
    case 'moderada_severa':
      return 'text-orange-500'
    case 'severa':
      return 'text-red-400'
    case 'profunda':
      return 'text-red-500'
    default:
      return 'text-dark-400'
  }
}

export default function HearingClassification({ classifications }: HearingClassificationProps) {
  if (classifications.length === 0) {
    return (
      <div className="text-[10px] text-dark-500 italic py-2">
        Ingrese umbrales para ver la clasificación automática.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {classifications.map(c => (
        <div
          key={c.ear}
          className="bg-dark-800/50 rounded-lg p-2 border border-dark-700/50"
        >
          <div className="flex items-center justify-between mb-1">
            <span className={`text-[10px] font-bold uppercase tracking-wider ${
              c.ear === 'od' ? 'text-red-400' : 'text-blue-400'
            }`}>
              {c.ear === 'od' ? 'Oído Derecho' : 'Oído Izquierdo'}
            </span>
            <span className="text-[10px] text-dark-400 font-mono">
              PTA: {c.pta.toFixed(1)} dB
            </span>
          </div>

          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[10px]">
            <div>
              <span className="text-dark-500">Tipo: </span>
              <span className="text-dark-200 font-medium">{typeLabel(c.type)}</span>
            </div>
            <div>
              <span className="text-dark-500">Grado: </span>
              <span className={`font-medium ${getGradeColor(c.grade)}`}>
                {gradeLabel(c.grade)}
              </span>
            </div>
            {c.gapDb > 0 && (
              <div className="col-span-2">
                <span className="text-dark-500">Gap A-O: </span>
                <span className="text-dark-200 font-mono">{c.gapDb.toFixed(1)} dB</span>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
