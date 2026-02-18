import { useState } from 'react'
import {
  Activity, Eye, MoveHorizontal, RotateCcw, Thermometer,
  ArrowLeft, PlayCircle, Target, LucideIcon,
  Ear, Mic, Volume2, Radio
} from 'lucide-react'
import { AppConfig, CaloricProtocol } from '../types/config'
import CaloricProtocolModal from './CaloricProtocolModal'
import PositionalProtocolModal from './PositionalProtocolModal'
import { TestBattery } from './settings/ModuleSelector'

interface TestSelectionViewProps {
  onSelectTest: (testType: string, protocol?: CaloricProtocol) => void
  onBack: () => void
  patientName: string
  caloricProtocols?: CaloricProtocol[]
  batteries?: TestBattery[]
  appConfig?: AppConfig | null
}

interface TestDef {
  id: string
  title: string
  description: string
  icon: LucideIcon
  color: string
  bg: string
  border: string
}

const TESTS: TestDef[] = [
  {
    id: 'spontaneous',
    title: 'Nistagmo Espontáneo',
    description: 'Evaluación de nistagmo sin fijación visual.',
    icon: Eye,
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/20'
  },
  {
    id: 'calibration_gaze',
    title: 'Calibración Ocular',
    description: 'Secuencia de puntos para calibrar el seguimiento.',
    icon: Target,
    color: 'text-pink-400',
    bg: 'bg-pink-500/10',
    border: 'border-pink-500/20'
  },
  {
    id: 'saccades',
    title: 'Sacadas',
    description: 'Aleatorias, fijas y anti-sacadas.',
    icon: MoveHorizontal,
    color: 'text-green-400',
    bg: 'bg-green-500/10',
    border: 'border-green-500/20'
  },
  {
    id: 'pursuit',
    title: 'Seguimiento Pendular',
    description: 'Sinusoidal, suma de senos y step-ramp.',
    icon: Activity,
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/20'
  },
  {
    id: 'positional',
    title: 'Pruebas Posicionales',
    description: 'Dix-Hallpike y cambios posturales (Mirada).',
    icon: RotateCcw,
    color: 'text-orange-400',
    bg: 'bg-orange-500/10',
    border: 'border-orange-500/20'
  },
  {
    id: 'caloric',
    title: 'Pruebas Calóricas',
    description: 'Estimulación térmica del oído interno.',
    icon: Thermometer,
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/20'
  },
  {
    id: 'optokinetic',
    title: 'Optocinético / Full Field',
    description: 'Barras, damero y movimiento visual completo.',
    icon: PlayCircle,
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
    border: 'border-cyan-500/20'
  }
]

const AUDIOMETRIA_TESTS: TestDef[] = [
  {
    id: 'audio_tonal_liminar',
    title: 'Audiometría Tonal Liminar',
    description: 'Umbrales auditivos por vía aérea y ósea.',
    icon: Ear,
    color: 'text-teal-400',
    bg: 'bg-teal-500/10',
    border: 'border-teal-500/20'
  },
  {
    id: 'audio_vocal',
    title: 'Audiometría Vocal',
    description: 'Discriminación del habla (logoaudiometría).',
    icon: Mic,
    color: 'text-teal-300',
    bg: 'bg-teal-400/10',
    border: 'border-teal-400/20'
  },
  {
    id: 'audio_supraliminar',
    title: 'Pruebas Supraliminares',
    description: 'SISI, Fowler y Tone Decay.',
    icon: Volume2,
    color: 'text-teal-500',
    bg: 'bg-teal-600/10',
    border: 'border-teal-600/20'
  },
  {
    id: 'audio_altas_frecuencias',
    title: 'Altas Frecuencias',
    description: 'Umbrales superiores a 8000 Hz.',
    icon: Radio,
    color: 'text-teal-200',
    bg: 'bg-teal-300/10',
    border: 'border-teal-300/20'
  }
]

const TEST_MAP = Object.fromEntries([...TESTS, ...AUDIOMETRIA_TESTS].map(t => [t.id, t]))

function TestSelectionView({ onSelectTest, onBack, patientName, caloricProtocols, batteries = [], appConfig }: TestSelectionViewProps) {
  const [showCaloricModal, setShowCaloricModal] = useState(false)
  const [showPositionalModal, setShowPositionalModal] = useState(false)

  const audioEnabled = appConfig?.modules?.audiometria ?? false
  const audioTests = appConfig?.audiometria?.tests
  const visibleAudioTests = audioEnabled
    ? AUDIOMETRIA_TESTS.filter(t => {
        const key = t.id.replace('audio_', '') as keyof typeof audioTests
        return audioTests ? audioTests[key] : true
      })
    : []

  const handleTestClick = (testId: string) => {
    if (testId === 'caloric' && caloricProtocols && caloricProtocols.length > 0) {
      setShowCaloricModal(true)
    } else if (testId === 'positional') {
      setShowPositionalModal(true)
    } else {
      onSelectTest(testId)
    }
  }

  return (
    <div className="h-full bg-dark-950 p-8 flex flex-col overflow-y-auto custom-scrollbar">
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={onBack}
          className="p-2 hover:bg-dark-800 rounded-full text-dark-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-6 h-6" />
        </button>
        <div className="w-10 h-10 rounded-lg bg-dark-900 border border-dark-800 flex items-center justify-center overflow-hidden">
          <img src="/mod_vng.png" alt="VNG" className="w-8 h-8 object-contain" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Nueva Evaluación</h1>
          <p className="text-dark-400 text-sm">
            {patientName === "Modo Captura Libre"
              ? "Inicie una prueba rápida sin registro de paciente."
              : <>Seleccione el protocolo para: <span className="text-siev-400 font-bold">{patientName}</span></>}
          </p>
        </div>
      </div>

      {/* Baterías de pruebas */}
      {batteries.length > 0 && (
        <>
          <div className="mb-4">
            <h2 className="text-xs font-semibold text-dark-500 uppercase tracking-wider mb-3">
              Baterías de pruebas
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-w-5xl mx-auto w-full">
              {batteries.map(battery => {
                const batteryTests = battery.testIds.map(id => TEST_MAP[id]).filter(Boolean)
                return (
                  <button
                    key={battery.id}
                    onClick={() => handleTestClick(battery.testIds[0])}
                    className="flex flex-col items-start p-5 rounded-xl border border-siev-500/20 bg-siev-500/5 hover:bg-siev-500/10 transition-all hover:scale-[1.02] group text-left"
                  >
                    <div className="flex items-center gap-3 mb-3 w-full">
                      <div className="w-10 h-10 rounded-lg bg-siev-600/20 border border-siev-500/30 flex items-center justify-center shrink-0">
                        <span className="text-sm font-bold text-siev-400 tracking-wider">
                          {battery.shortName.slice(0, 3)}
                        </span>
                      </div>
                      <div className="min-w-0">
                        <h3 className="text-base font-bold text-white truncate group-hover:text-siev-400 transition-colors">
                          {battery.name}
                        </h3>
                        <span className="text-[10px] text-dark-500 uppercase tracking-wider">{battery.shortName}</span>
                      </div>
                    </div>

                    {battery.description && (
                      <p className="text-xs text-dark-400 mb-3 line-clamp-2">{battery.description}</p>
                    )}

                    <div className="flex items-center gap-1.5 flex-wrap">
                      {batteryTests.map(test => {
                        const Icon = test.icon
                        return (
                          <div
                            key={test.id}
                            className={`w-6 h-6 rounded flex items-center justify-center ${test.bg} border ${test.border}`}
                            title={test.title}
                          >
                            <Icon className={`w-3.5 h-3.5 ${test.color}`} />
                          </div>
                        )
                      })}
                      <span className="text-[10px] text-dark-500 ml-1">
                        {battery.testIds.length} prueba{battery.testIds.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="border-t border-dark-800 my-6 max-w-5xl mx-auto w-full" />
        </>
      )}

      {/* Pruebas VNG */}
      <div>
        <h2 className="text-xs font-semibold text-dark-500 uppercase tracking-wider mb-3">
          VNG — Pruebas individuales
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto w-full">
          {TESTS.map((test) => {
            const Icon = test.icon
            return (
              <button
                key={test.id}
                onClick={() => handleTestClick(test.id)}
                className={`flex flex-col items-start p-6 rounded-xl border ${test.border} ${test.bg} hover:bg-opacity-20 transition-all hover:scale-[1.02] group text-left`}
              >
                <div className={`p-3 rounded-lg bg-dark-950/50 mb-4 ${test.color}`}>
                  <Icon className="w-8 h-8" />
                </div>
                <h3 className="text-lg font-bold text-white mb-2 group-hover:text-siev-400 transition-colors">
                  {test.title}
                </h3>
                <p className="text-sm text-dark-300">
                  {test.description}
                </p>
              </button>
            )
          })}
        </div>
      </div>

      {/* Pruebas de Audiometría */}
      {visibleAudioTests.length > 0 && (
        <>
          <div className="border-t border-dark-800 my-6 max-w-5xl mx-auto w-full" />
          <div>
            <h2 className="text-xs font-semibold text-dark-500 uppercase tracking-wider mb-3">
              Audiometría — Pruebas individuales
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto w-full">
              {visibleAudioTests.map((test) => {
                const Icon = test.icon
                return (
                  <button
                    key={test.id}
                    onClick={() => handleTestClick(test.id)}
                    className={`flex flex-col items-start p-6 rounded-xl border ${test.border} ${test.bg} hover:bg-opacity-20 transition-all hover:scale-[1.02] group text-left`}
                  >
                    <div className={`p-3 rounded-lg bg-dark-950/50 mb-4 ${test.color}`}>
                      <Icon className="w-8 h-8" />
                    </div>
                    <h3 className="text-lg font-bold text-white mb-2 group-hover:text-siev-400 transition-colors">
                      {test.title}
                    </h3>
                    <p className="text-sm text-dark-300">
                      {test.description}
                    </p>
                  </button>
                )
              })}
            </div>
          </div>
        </>
      )}

      {showCaloricModal && caloricProtocols && (
        <CaloricProtocolModal
          protocols={caloricProtocols}
          onSelect={(protocol) => {
            setShowCaloricModal(false)
            onSelectTest('caloric', protocol)
          }}
          onCancel={() => setShowCaloricModal(false)}
        />
      )}

      {showPositionalModal && (
        <PositionalProtocolModal
          enabledTests={appConfig?.postural?.enabled_tests ?? []}
          customTests={appConfig?.postural?.custom_tests ?? []}
          onSelect={(test) => {
            setShowPositionalModal(false)
            onSelectTest(test.id)
          }}
          onCancel={() => setShowPositionalModal(false)}
        />
      )}
    </div>
  )
}

export default TestSelectionView
