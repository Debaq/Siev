import { CircleDot, ChevronRight, Activity } from 'lucide-react'

interface StatusBarProps {
  fps: number
  recording: boolean
  testType?: string | null
  patientName?: string | null
  onSelectTest?: () => void
  onSelectPatient?: () => void
}

function StatusBar({
  fps,
  recording,
  testType,
  patientName,
  onSelectTest,
  onSelectPatient
}: StatusBarProps) {
  // Map test IDs to readable labels
  const getTestLabel = (id: string) => {
    const labels: Record<string, string> = {
      'spontaneous': 'Nistagmo Espontáneo',
      'saccades': 'Sacadas',
      'pursuit': 'Seguimiento Pendular',
      'positional': 'Pruebas Posicionales',
      'caloric': 'Pruebas Calóricas',
      'optokinetic': 'Optocinético',
      'audio_tonal_liminar': 'Audiometría Tonal Liminar',
      'audio_vocal': 'Audiometría Vocal',
      'audio_supraliminar': 'Pruebas Supraliminares',
      'audio_altas_frecuencias': 'Altas Frecuencias',
    }
    return labels[id] || id;
  }

  return (
    <header className="bg-dark-900 border-b border-dark-800 px-4 py-2">
      <div className="flex items-center justify-between">
        {/* Module, Patient & Test Info */}
        <div className="flex items-center gap-3">
          <div className="flex flex-col pr-1">
            <h1 className="text-sm font-bold text-white tracking-tight uppercase">
              {testType?.startsWith('audio_') ? 'Evaluación Auditiva' : 'Video-Oculografía'}
            </h1>
            <p className="text-[10px] text-dark-500 font-medium">
              {testType?.startsWith('audio_') ? 'Evaluación Audiológica' : 'Protocolos VNG'}
            </p>
          </div>

          <div className="h-6 w-px bg-dark-700 mx-1" />

          {/* Patient Info */}
          {patientName ? (
            <div className="flex items-center gap-2 bg-green-500/10 px-3 py-1 rounded-lg border border-green-500/20">
              <span className="text-[10px] font-bold text-green-500 uppercase tracking-wider">Paciente:</span>
              <span className="text-xs font-semibold text-white">{patientName}</span>
              <button 
                onClick={onSelectPatient}
                className="ml-1 p-0.5 hover:bg-green-500/20 rounded transition-colors text-green-500"
                title="Cambiar paciente"
              >
                <ChevronRight className="w-3 h-3" />
              </button>
            </div>
          ) : (
            <button 
              onClick={onSelectPatient}
              className="flex items-center gap-2 bg-dark-800 hover:bg-dark-700 px-3 py-1 rounded-lg border border-dark-700 transition-all group"
            >
              <Activity className="w-3 h-3 text-dark-400 group-hover:text-green-500" />
              <span className="text-[11px] font-bold text-dark-300 group-hover:text-white uppercase">Seleccionar Paciente</span>
              <ChevronRight className="w-3 h-3 text-dark-500 group-hover:text-green-500" />
            </button>
          )}

          {/* Test Info */}
          {testType ? (
            <div className="flex items-center gap-2 bg-siev-500/10 px-3 py-1 rounded-lg border border-siev-500/20">
              <span className="text-[10px] font-bold text-siev-400 uppercase tracking-wider">Prueba:</span>
              <span className="text-xs font-semibold text-white">{getTestLabel(testType)}</span>
              <button 
                onClick={onSelectTest}
                className="ml-1 p-0.5 hover:bg-siev-500/20 rounded transition-colors text-siev-400"
                title="Cambiar prueba"
              >
                <ChevronRight className="w-3 h-3" />
              </button>
            </div>
          ) : (
            <button 
              onClick={onSelectTest}
              className="flex items-center gap-2 bg-dark-800 hover:bg-dark-700 px-3 py-1 rounded-lg border border-dark-700 transition-all group"
            >
              <Activity className="w-3 h-3 text-dark-400 group-hover:text-siev-400" />
              <span className="text-[11px] font-bold text-dark-300 group-hover:text-white uppercase">Protocolo</span>
              <ChevronRight className="w-3 h-3 text-dark-500 group-hover:text-siev-400" />
            </button>
          )}
        </div>

        {/* Status Indicators */}
        <div className="flex items-center gap-6">
          {/* FPS */}
          {fps > 0 && (
            <div className="flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-siev-400" />
              <span className="text-sm text-siev-400 font-mono">
                {fps.toFixed(1)} FPS
              </span>
            </div>
          )}

          {/* Recording Indicator */}
          {recording && (
            <>
              <div className="w-px h-6 bg-dark-700" />
              <div className="flex items-center gap-1.5 text-red-400">
                <CircleDot className="w-4 h-4 animate-pulse" />
                <span className="text-sm font-medium">REC</span>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}

export default StatusBar
