import { Save, Trash2, FileText } from 'lucide-react'
import type { AudiometrySubView, HearingClassificationResult } from '../../types/audiometry'
import HearingClassification from './tonal/HearingClassification'

interface AudiometryControlPanelProps {
  activeSubView: AudiometrySubView
  classifications: HearingClassificationResult[]
  notes: string
  saving: boolean
  onSetSubView: (v: AudiometrySubView) => void
  onSetNotes: (n: string) => void
  onSave: () => void
  onClear: () => void
}

const SUB_VIEWS: { id: AudiometrySubView; label: string }[] = [
  { id: 'tonal', label: 'Audiometría' },
  { id: 'supraliminar', label: 'Supraliminares' },
  { id: 'alta_frecuencia', label: 'Altas Frec.' },
]

export default function AudiometryControlPanel({
  activeSubView,
  classifications,
  notes,
  saving,
  onSetSubView,
  onSetNotes,
  onSave,
  onClear,
}: AudiometryControlPanelProps) {
  return (
    <div className="h-full flex flex-col">
      <div className="p-3 border-b border-dark-800 font-bold text-dark-300 text-[11px] uppercase tracking-wider bg-dark-850">
        Panel de Control
      </div>

      <div className="flex-1 overflow-y-auto p-3 custom-scrollbar space-y-3">
        {/* Sub-vista */}
        <div>
          <div className="text-[10px] font-bold text-dark-400 uppercase tracking-wider mb-1.5">Prueba</div>
          <div className="flex flex-col gap-1">
            {SUB_VIEWS.map(sv => (
              <button
                key={sv.id}
                onClick={() => onSetSubView(sv.id)}
                className={`px-2 py-1.5 rounded text-[10px] font-medium transition-colors text-left ${
                  activeSubView === sv.id || (sv.id === 'tonal' && activeSubView === 'vocal')
                    ? 'bg-siev-600 text-white'
                    : 'bg-dark-800 text-dark-400 hover:text-dark-200 hover:bg-dark-700'
                }`}
              >
                {sv.label}
              </button>
            ))}
          </div>
        </div>

        {/* Clasificación */}
        <div>
          <div className="text-[10px] font-bold text-dark-400 uppercase tracking-wider mb-1.5">Clasificación</div>
          <HearingClassification classifications={classifications} />
        </div>

        {/* Notas */}
        <div>
          <div className="text-[10px] font-bold text-dark-400 uppercase tracking-wider mb-1.5 flex items-center gap-1">
            <FileText className="w-3 h-3" />
            Notas Clínicas
          </div>
          <textarea
            value={notes}
            onChange={e => onSetNotes(e.target.value)}
            className="w-full bg-dark-800 border border-dark-700 rounded px-2 py-1.5 text-[10px] text-dark-200 resize-none h-16 custom-scrollbar"
            placeholder="Observaciones..."
          />
        </div>
      </div>

      {/* Acciones fijas abajo */}
      <div className="p-3 border-t border-dark-800 space-y-1.5">
        <button
          onClick={onSave}
          disabled={saving}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-siev-600 hover:bg-siev-500 disabled:bg-dark-700 disabled:text-dark-500 rounded text-xs font-medium text-white transition-colors"
        >
          <Save className="w-3.5 h-3.5" />
          {saving ? 'Guardando...' : 'Guardar'}
        </button>
        <button
          onClick={onClear}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 bg-dark-800 hover:bg-dark-700 rounded text-[10px] text-dark-400 hover:text-red-400 transition-colors"
        >
          <Trash2 className="w-3 h-3" />
          Limpiar todo
        </button>
      </div>
    </div>
  )
}
