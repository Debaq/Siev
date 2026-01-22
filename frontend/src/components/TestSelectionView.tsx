import { 
  Activity, Eye, MoveHorizontal, RotateCcw, Thermometer, 
  ArrowLeft, PlayCircle 
} from 'lucide-react'

interface TestSelectionViewProps {
  onSelectTest: (testType: string) => void
  onBack: () => void
  patientName: string
}

const TESTS = [
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
    id: 'saccades',
    title: 'Sacadas',
    description: 'Movimientos oculares rápidos entre puntos fijos.',
    icon: MoveHorizontal,
    color: 'text-green-400',
    bg: 'bg-green-500/10',
    border: 'border-green-500/20'
  },
  {
    id: 'pursuit',
    title: 'Seguimiento Pendular',
    description: 'Seguimiento suave de un objetivo móvil.',
    icon: Activity,
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/20'
  },
  {
    id: 'positional',
    title: 'Pruebas Posicionales',
    description: 'Dix-Hallpike y cambios posturales.',
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
    title: 'Optocinético',
    description: 'Respuesta a estímulos visuales en movimiento.',
    icon: PlayCircle,
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
    border: 'border-cyan-500/20'
  }
]

function TestSelectionView({ onSelectTest, onBack, patientName }: TestSelectionViewProps) {
  return (
    <div className="h-full bg-dark-950 p-8 flex flex-col">
      <div className="flex items-center gap-4 mb-8">
        <button 
          onClick={onBack}
          className="p-2 hover:bg-dark-800 rounded-full text-dark-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-6 h-6" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">Nueva Evaluación</h1>
          <p className="text-dark-400 text-sm">Seleccione el protocolo para: <span className="text-siev-400 font-bold">{patientName}</span></p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto w-full">
        {TESTS.map((test) => {
          const Icon = test.icon
          return (
            <button
              key={test.id}
              onClick={() => onSelectTest(test.id)}
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
  )
}

export default TestSelectionView
