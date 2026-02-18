import { useState } from 'react'
import {
    RotateCcw, Play, Pause, SkipForward, Square,
    ChevronDown, Activity, Eye, Crosshair, ClipboardList, Check, X, AlertTriangle
} from 'lucide-react'
import { PosturalTestDefinition, PosturalSymptomsConfig } from '../../types/config'
import { UsePosturalProtocolReturn, PosturalStage } from '../../hooks/usePosturalProtocol'
import { UsePosturalTimerReturn } from '../../hooks/usePosturalTimer'
import { UseImuDataReturn } from '../../hooks/useImuData'
import PosturalTestSelector from './PosturalTestSelector'

interface AccordionSectionProps {
    id: string
    icon: any
    title: string
    children: React.ReactNode
    openSection: string
    onToggle: (id: string) => void
}

function AccordionSection({ id, icon: Icon, title, children, openSection, onToggle }: AccordionSectionProps) {
    const isOpen = openSection === id
    return (
        <div className="border-b border-dark-700/50">
            <button
                onClick={() => onToggle(id)}
                className="flex items-center justify-between w-full py-2 px-1 text-left hover:bg-dark-800/50 transition-colors rounded"
            >
                <div className="flex items-center gap-1.5">
                    <Icon className="w-3 h-3 text-dark-400" />
                    <span className="text-[10px] uppercase font-bold text-dark-400">{title}</span>
                </div>
                <ChevronDown className={`w-3 h-3 text-dark-500 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
            </button>
            <div className={`overflow-hidden transition-all duration-200 ${isOpen ? 'max-h-[600px] opacity-100' : 'max-h-0 opacity-0'}`}>
                <div className="pb-3 px-1">{children}</div>
            </div>
        </div>
    )
}

function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

interface PosturalControlPanelProps {
    protocol: UsePosturalProtocolReturn
    timer: UsePosturalTimerReturn
    imu: UseImuDataReturn
    symptomsConfig?: PosturalSymptomsConfig
    enabledTests: string[]
    customTests?: PosturalTestDefinition[]
    onStartTest: (test: PosturalTestDefinition) => void
    onAdvance: () => void
    onSkip: () => void
    onPause: () => void
    onResume: () => void
    onStop: () => void
    onReset: () => void
}

const stageStatusIcon = (stage: PosturalStage, index: number) => {
    switch (stage.status) {
        case 'completed': return <Check className="w-2.5 h-2.5" />
        case 'skipped': return <X className="w-2.5 h-2.5" />
        case 'active': return <span className="text-[9px] font-bold">{index + 1}</span>
        default: return <span className="text-[9px]">{index + 1}</span>
    }
}

const stageStatusColor = (stage: PosturalStage) => {
    switch (stage.status) {
        case 'completed': return 'bg-green-600 text-white'
        case 'skipped': return 'bg-yellow-500 text-white'
        case 'active': return 'bg-orange-500 text-white'
        default: return 'bg-dark-700 text-dark-400'
    }
}

export default function PosturalControlPanel({
    protocol,
    timer,
    imu,
    symptomsConfig,
    enabledTests,
    customTests,
    onStartTest,
    onAdvance,
    onSkip,
    onPause,
    onResume,
    onStop,
    onReset,
}: PosturalControlPanelProps) {
    const [openSection, setOpenSection] = useState<string>(protocol.isActive ? 'position' : 'protocol')
    const [observationText, setObservationText] = useState('')

    const toggleSection = (id: string) => setOpenSection(prev => prev === id ? '' : id)

    const currentStage = protocol.isActive && protocol.currentStageIndex >= 0
        ? protocol.stages[protocol.currentStageIndex]
        : null

    return (
        <div className="flex flex-col h-full">
            <div className="flex justify-between items-center mb-3">
                <h2 className="text-xs font-bold text-dark-300 uppercase tracking-wider">VPPB</h2>
            </div>

            {/* Protocol section */}
            <AccordionSection id="protocol" icon={ClipboardList} title="Protocolo" openSection={openSection} onToggle={toggleSection}>
                {!protocol.isActive && !protocol.isComplete ? (
                    <PosturalTestSelector
                        enabledTests={enabledTests}
                        customTests={customTests}
                        onSelect={onStartTest}
                        onClose={() => {}}
                    />
                ) : (
                    <div className="space-y-1.5">
                        <div className="flex items-center gap-2 mb-2">
                            <RotateCcw className="w-3.5 h-3.5 text-orange-400" />
                            <span className="text-xs font-semibold text-white">{protocol.test?.name}</span>
                        </div>
                        {protocol.stages.map((stage, i) => (
                            <div
                                key={i}
                                onClick={() => {
                                    if (!timer.isRunning && stage.status === 'pending') {
                                        protocol.goToStage(i)
                                    }
                                }}
                                className={`flex items-center gap-2 px-2 py-1.5 rounded text-xs transition-colors ${
                                    stage.status === 'active'
                                        ? 'bg-orange-500/15 border border-orange-500/30'
                                        : stage.status === 'completed'
                                        ? 'bg-dark-800/50 border border-dark-700/50'
                                        : stage.status === 'skipped'
                                        ? 'bg-yellow-500/10 border border-yellow-500/20'
                                        : 'bg-dark-800/30 border border-transparent cursor-pointer hover:bg-dark-800/60'
                                } ${timer.isRunning ? 'pointer-events-none' : ''}`}
                            >
                                <span className={`w-4 h-4 rounded-full flex items-center justify-center shrink-0 ${stageStatusColor(stage)}`}>
                                    {stageStatusIcon(stage, i)}
                                </span>
                                <span className={`font-medium flex-1 truncate ${
                                    stage.status === 'active' ? 'text-orange-400' :
                                    stage.status === 'completed' ? 'text-dark-400' :
                                    'text-dark-300'
                                }`}>
                                    {stage.position.label}
                                </span>
                                {stage.nystagmusDetected && (
                                    <AlertTriangle className="w-3 h-3 text-yellow-400 shrink-0" />
                                )}
                                {stage.status === 'active' && (
                                    <span className="text-[9px] text-orange-400 font-bold uppercase">Activa</span>
                                )}
                            </div>
                        ))}

                        {protocol.isComplete && (
                            <div className="flex items-center gap-2 px-2 py-2 rounded bg-green-500/10 border border-green-500/20 text-xs text-green-400 font-bold mt-2">
                                <Check className="w-3.5 h-3.5" />
                                Test Completado
                            </div>
                        )}

                        <button
                            onClick={onReset}
                            className="btn btn-secondary w-full mt-2 text-[10px] h-7"
                            disabled={timer.isRunning}
                        >
                            <RotateCcw className="w-3 h-3" />
                            Nuevo Test
                        </button>
                    </div>
                )}
            </AccordionSection>

            {/* Current Position */}
            {protocol.isActive && currentStage && (
                <AccordionSection id="position" icon={Activity} title="Posición Actual" openSection={openSection} onToggle={toggleSection}>
                    <div className="space-y-3">
                        {/* Instruction */}
                        <div className="bg-dark-800 rounded-lg p-3 border border-dark-700">
                            <p className="text-sm text-white font-medium mb-1">{currentStage.position.label}</p>
                            <p className="text-xs text-dark-300">{currentStage.position.description}</p>
                        </div>

                        {/* Timer */}
                        <div className="text-center">
                            <div className="text-3xl font-mono font-bold text-white tabular-nums">
                                {timer.isRunning || timer.isPaused
                                    ? formatTime(timer.remainingSeconds)
                                    : formatTime(currentStage.duration)
                                }
                            </div>
                            {timer.isRunning && (
                                <div className="w-full h-1.5 bg-dark-800 rounded-full mt-2 overflow-hidden">
                                    <div
                                        className="h-full bg-orange-500 rounded-full transition-[width] duration-100 ease-linear"
                                        style={{ width: `${timer.progress * 100}%` }}
                                    />
                                </div>
                            )}
                        </div>

                        {/* Controls */}
                        <div className="grid grid-cols-3 gap-1.5">
                            {!timer.isRunning && !timer.isPaused ? (
                                <button onClick={onAdvance} className="btn btn-primary col-span-3 h-8">
                                    <Play className="w-3.5 h-3.5" />
                                    INICIAR
                                </button>
                            ) : timer.isPaused ? (
                                <>
                                    <button onClick={onResume} className="btn btn-primary col-span-2 h-8">
                                        <Play className="w-3 h-3" />
                                        REANUDAR
                                    </button>
                                    <button onClick={onStop} className="btn btn-danger h-8">
                                        <Square className="w-3 h-3" />
                                    </button>
                                </>
                            ) : (
                                <>
                                    <button onClick={onPause} className="btn btn-secondary h-8">
                                        <Pause className="w-3 h-3" />
                                    </button>
                                    <button onClick={onSkip} className="btn btn-secondary h-8">
                                        <SkipForward className="w-3 h-3" />
                                    </button>
                                    <button onClick={onStop} className="btn btn-danger h-8">
                                        <Square className="w-3 h-3" />
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                </AccordionSection>
            )}

            {/* Observations */}
            {protocol.isActive && currentStage && (
                <AccordionSection id="observations" icon={Eye} title="Observaciones" openSection={openSection} onToggle={toggleSection}>
                    <div className="space-y-2">
                        {/* Nystagmus quick checkboxes */}
                        <div className="flex items-center gap-2">
                            <label className="flex items-center gap-1.5 text-xs text-dark-300 cursor-pointer">
                                <input
                                    type="checkbox"
                                    className="rounded border-dark-600"
                                    checked={currentStage.nystagmusDetected ?? false}
                                    onChange={(e) => protocol.markNystagmus(protocol.currentStageIndex, e.target.checked)}
                                />
                                Nistagmo
                            </label>
                            {currentStage.nystagmusDetected && (
                                <select
                                    className="select h-6 text-[10px] w-auto"
                                    value={currentStage.nystagmusDirection ?? ''}
                                    onChange={(e) => protocol.markNystagmus(protocol.currentStageIndex, true, e.target.value)}
                                >
                                    <option value="">Dirección...</option>
                                    <option value="geotrópico">Geotrópico</option>
                                    <option value="ageotrópico">Ageotrópico</option>
                                    <option value="up-beating">Up-beating</option>
                                    <option value="down-beating">Down-beating</option>
                                    <option value="derecha">Derecha</option>
                                    <option value="izquierda">Izquierda</option>
                                    <option value="rotatorio">Rotatorio</option>
                                </select>
                            )}
                        </div>

                        {/* Subjective Symptoms — only for provocation tests */}
                        {protocol.test?.category === 'provocation' && symptomsConfig && (
                            <div className="space-y-1.5 pt-1">
                                <div className="flex items-center justify-between">
                                    <span className="text-[10px] font-bold text-dark-500 uppercase">S&iacute;ntomas subjetivos</span>
                                    <span className="text-[9px] text-dark-600">
                                        {symptomsConfig.scale.type === 'vas_0_10' ? '0-10' : '0-4'}
                                    </span>
                                </div>
                                {symptomsConfig.symptoms.filter(s => s.enabled).map(symptom => {
                                    const max = symptomsConfig.scale.type === 'vas_0_10' ? 10 : 4
                                    const currentValue = currentStage?.symptoms.find(
                                        r => r.symptom_id === symptom.id
                                    )?.value ?? 0
                                    return (
                                        <div key={symptom.id} className="flex items-center gap-2">
                                            <span className="text-[10px] text-dark-300 w-16 shrink-0 truncate">{symptom.label}</span>
                                            <input
                                                type="range"
                                                min={0}
                                                max={max}
                                                step={1}
                                                value={currentValue}
                                                onChange={(e) => protocol.setSymptom(
                                                    protocol.currentStageIndex,
                                                    symptom.id,
                                                    parseInt(e.target.value)
                                                )}
                                                className="flex-1 h-1 accent-orange-500"
                                            />
                                            <span className="text-[10px] font-mono font-bold text-white w-5 text-right">
                                                {currentValue}
                                            </span>
                                        </div>
                                    )
                                })}
                            </div>
                        )}

                        {/* Notes */}
                        <textarea
                            className="input w-full h-16 text-xs resize-none"
                            placeholder="Notas de observación..."
                            value={observationText}
                            onChange={(e) => {
                                setObservationText(e.target.value)
                                protocol.addObservation(protocol.currentStageIndex, e.target.value)
                            }}
                        />
                    </div>
                </AccordionSection>
            )}

            {/* IMU */}
            <AccordionSection id="imu" icon={Crosshair} title="IMU" openSection={openSection} onToggle={toggleSection}>
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <span className="text-[10px] text-dark-400">Calibración</span>
                        <span className={`text-[10px] font-bold ${imu.isCalibrated ? 'text-green-400' : 'text-yellow-400'}`}>
                            {imu.isCalibrated ? 'Calibrada' : 'Sin calibrar'}
                        </span>
                    </div>

                    {imu.current && (
                        <div className="grid grid-cols-3 gap-1.5 text-center">
                            <div className="bg-dark-800 rounded p-1.5 border border-dark-700">
                                <div className="text-[9px] text-yellow-400 font-bold">YAW</div>
                                <div className="text-xs font-mono text-white">{imu.current.calibrated.yaw.toFixed(1)}°</div>
                            </div>
                            <div className="bg-dark-800 rounded p-1.5 border border-dark-700">
                                <div className="text-[9px] text-green-400 font-bold">PITCH</div>
                                <div className="text-xs font-mono text-white">{imu.current.calibrated.pitch.toFixed(1)}°</div>
                            </div>
                            <div className="bg-dark-800 rounded p-1.5 border border-dark-700">
                                <div className="text-[9px] text-blue-400 font-bold">ROLL</div>
                                <div className="text-xs font-mono text-white">{imu.current.calibrated.roll.toFixed(1)}°</div>
                            </div>
                        </div>
                    )}

                    <div className="flex gap-1.5">
                        <button
                            onClick={imu.calibrate}
                            className="btn btn-primary flex-1 text-[10px] h-7"
                        >
                            <Crosshair className="w-3 h-3" />
                            {imu.isCalibrated ? 'Recalibrar' : 'Calibrar'}
                        </button>
                        {imu.isCalibrated && (
                            <button
                                onClick={imu.resetCalibration}
                                className="btn btn-secondary text-[10px] h-7 px-2"
                            >
                                <RotateCcw className="w-3 h-3" />
                            </button>
                        )}
                    </div>
                </div>
            </AccordionSection>
        </div>
    )
}
