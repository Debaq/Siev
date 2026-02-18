import React, { useState, useMemo, useCallback } from 'react'
import {
    RotateCcw, ArrowLeft, Copy, Trash2, Plus, GripVertical,
    Shield, Play, Pause, Square, ChevronDown, ChevronRight,
} from 'lucide-react'
import { AppConfig, PosturalTestDefinition, PosturalPosition, BodyPosition } from '../../../types/config'
import { getAllTestsByCategory, isBaseTest, createEmptyTest } from '../../../data/vppbTests'
import { usePhasePlayback } from '../../../hooks/usePhasePlayback'
import PhaseTimeline from './PhaseTimeline'
import OrientationGauges from './OrientationGauges'
import BodyPositionIcon from './BodyPositionIcon'

interface TestsTabProps {
    config: AppConfig
    updateConfig: (path: string, value: any) => void
}

// ── SecondsSpin ───────────────────────────────────────────────────────
const SecondsSpin: React.FC<{
    value: number; onChange: (v: number) => void
    min?: number; max?: number; step?: number; label?: string
}> = ({ value, onChange, min = 0, max = 600, step = 1, label }) => (
    <div className="flex items-center gap-2">
        <input
            type="number"
            className="input h-8 w-20 text-sm text-center font-mono"
            value={value} min={min} max={max} step={step}
            onChange={e => {
                const v = Number(e.target.value)
                if (!isNaN(v) && v >= min && v <= max) onChange(v)
            }}
        />
        <span className="text-xs text-dark-500">{label ?? 's'}</span>
    </div>
)

// ── OrientationSlider ─────────────────────────────────────────────────
const OrientationSlider: React.FC<{
    label: string; value: number; onChange: (v: number) => void
    min: number; max: number; color: string
}> = ({ label, value, onChange, min, max, color }) => (
    <div className="flex items-center gap-2">
        <span className={`text-xs font-mono w-10 ${color}`}>{label}</span>
        <input
            type="range"
            className="flex-1 h-1.5 accent-orange-500"
            min={min} max={max} step={5} value={value}
            onChange={e => onChange(Number(e.target.value))}
        />
        <input
            type="number"
            className="input h-7 w-16 text-xs text-center font-mono"
            value={value} min={min} max={max} step={5}
            onChange={e => {
                const v = Number(e.target.value)
                if (!isNaN(v) && v >= min && v <= max) onChange(v)
            }}
        />
        <span className="text-[10px] text-dark-500">°</span>
    </div>
)

// ══════════════════════════════════════════════════════════════════════
export const TestsTab: React.FC<TestsTabProps> = ({ config, updateConfig }) => {
    const enabledTests = config.postural?.enabled_tests ?? []
    const customTests = config.postural?.custom_tests ?? []
    const timing = config.postural?.timing ?? { auto_advance: false, countdown_sound: true }

    const [editingTestId, setEditingTestId] = useState<string | null>(null)
    const [selectedPhaseIndex, setSelectedPhaseIndex] = useState(0)
    const [dragIndex, setDragIndex] = useState<number | null>(null)

    const { provocation, liberation, repositioning, all, map: testMap } = useMemo(
        () => getAllTestsByCategory(customTests),
        [customTests],
    )

    // ── CRUD ───────────────────────────────────────────────────────
    const toggleTest = (testId: string) => {
        const newEnabled = enabledTests.includes(testId)
            ? enabledTests.filter((id: string) => id !== testId)
            : [...enabledTests, testId]
        updateConfig('postural.enabled_tests', newEnabled)
    }

    const allIds = all.map(t => t.id)
    const allEnabled = allIds.length > 0 && allIds.every(id => enabledTests.includes(id))

    const toggleAll = () => {
        updateConfig('postural.enabled_tests', allEnabled ? [] : allIds)
    }

    const createNewTest = () => {
        const test = createEmptyTest()
        updateConfig('postural.custom_tests', [...customTests, test])
        setEditingTestId(test.id)
        setSelectedPhaseIndex(0)
    }

    const duplicateTest = (source: PosturalTestDefinition) => {
        const id = `custom_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
        const copy: PosturalTestDefinition = {
            ...JSON.parse(JSON.stringify(source)),
            id,
            name: `${source.name} (copia)`,
        }
        // Generate new IDs for positions
        copy.positions = copy.positions.map((p, i) => ({
            ...p,
            id: `pos_${i}_${Math.random().toString(36).slice(2, 7)}`,
        }))
        updateConfig('postural.custom_tests', [...customTests, copy])
        setEditingTestId(copy.id)
        setSelectedPhaseIndex(0)
    }

    const deleteTest = (testId: string) => {
        if (isBaseTest(testId)) return
        if (editingTestId === testId) setEditingTestId(null)
        updateConfig('postural.custom_tests', customTests.filter(t => t.id !== testId))
        updateConfig('postural.enabled_tests', enabledTests.filter((id: string) => id !== testId))
    }

    const updateCustomTest = useCallback((updated: PosturalTestDefinition) => {
        const idx = customTests.findIndex(t => t.id === updated.id)
        if (idx < 0) return
        const newList = [...customTests]
        newList[idx] = updated
        updateConfig('postural.custom_tests', newList)
    }, [customTests, updateConfig])

    /** If editing a base test, fork it into a custom copy, apply the update, and switch to editing the copy. */
    const forkOrUpdate = useCallback((test: PosturalTestDefinition, updated: PosturalTestDefinition) => {
        if (!isBaseTest(test.id)) {
            // Already custom — just update
            updateCustomTest(updated)
            return
        }
        // Fork: create custom copy with new id
        const id = `custom_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
        const copy: PosturalTestDefinition = {
            ...JSON.parse(JSON.stringify(updated)),
            id,
        }
        copy.positions = copy.positions.map((p, i) => ({
            ...p,
            id: `pos_${i}_${Math.random().toString(36).slice(2, 7)}`,
        }))
        updateConfig('postural.custom_tests', [...customTests, copy])
        setEditingTestId(copy.id)
    }, [customTests, updateConfig, updateCustomTest])

    // ── Playback ──────────────────────────────────────────────────
    const playback = usePhasePlayback((newIndex) => {
        setSelectedPhaseIndex(newIndex)
    })

    // ── Find editing test ─────────────────────────────────────────
    const editingTest = editingTestId ? (testMap[editingTestId] ?? customTests.find(t => t.id === editingTestId)) : null

    // ════════════════════════════════════════════════════════════════
    // DETAIL VIEW
    // ════════════════════════════════════════════════════════════════
    if (editingTest && editingTestId) {
        const test = editingTest
        const isBase = isBaseTest(test.id)
        const phases = test.positions
        const selectedPhase = phases[selectedPhaseIndex] ?? phases[0]

        const updateField = (field: keyof PosturalTestDefinition, value: any) => {
            forkOrUpdate(test, { ...test, [field]: value })
        }

        const updatePhase = (phaseIdx: number, patch: Partial<PosturalPosition>) => {
            const newPositions = [...phases]
            newPositions[phaseIdx] = { ...newPositions[phaseIdx], ...patch }
            forkOrUpdate(test, { ...test, positions: newPositions })
        }

        const updatePhaseOrientation = (phaseIdx: number, axis: 'yaw' | 'pitch' | 'roll', value: number) => {
            const phase = phases[phaseIdx]
            const current = phase.target_head_orientation ?? { yaw: 0, pitch: 0, roll: 0 }
            updatePhase(phaseIdx, { target_head_orientation: { ...current, [axis]: value } })
        }

        const addPhase = () => {
            const newPhase: PosturalPosition = {
                id: `pos_${phases.length}_${Math.random().toString(36).slice(2, 7)}`,
                label: `Posición ${phases.length + 1}`,
                description: '',
                default_duration_seconds: 10,
                target_head_orientation: { yaw: 0, pitch: 0, roll: 0 },
            }
            forkOrUpdate(test, { ...test, positions: [...phases, newPhase] })
            setSelectedPhaseIndex(phases.length)
        }

        const removePhase = (idx: number) => {
            if (phases.length <= 1) return
            const newPositions = phases.filter((_, i) => i !== idx)
            forkOrUpdate(test, { ...test, positions: newPositions })
            if (selectedPhaseIndex >= newPositions.length) {
                setSelectedPhaseIndex(newPositions.length - 1)
            }
        }

        const movePhase = (from: number, to: number) => {
            if (to < 0 || to >= phases.length) return
            const list = [...phases]
            const [moved] = list.splice(from, 1)
            list.splice(to, 0, moved)
            forkOrUpdate(test, { ...test, positions: list })
            if (selectedPhaseIndex === from) setSelectedPhaseIndex(to)
        }

        const currentOrientation = selectedPhase?.target_head_orientation ?? { yaw: 0, pitch: 0, roll: 0 }

        return (
            <div className="space-y-4 py-4 animate-fade-in">
                {/* Back */}
                <button
                    onClick={() => { setEditingTestId(null); playback.stop() }}
                    className="flex items-center gap-2 text-sm text-dark-300 hover:text-white transition-colors"
                >
                    <ArrowLeft size={16} /> Volver a pruebas
                </button>

                {/* Header */}
                <div className="flex items-center gap-3">
                    <RotateCcw size={20} className="text-orange-400" />
                    <h2 className="text-lg font-bold text-white">{test.name}</h2>
                    {isBase && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium bg-amber-500/15 text-amber-400 rounded border border-amber-500/20">
                            <Shield size={10} /> Base — al editar se crea copia
                        </span>
                    )}
                </div>

                {/* Two-column layout */}
                <div className="flex gap-4" style={{ minHeight: 480 }}>
                    {/* LEFT — metadata + phases */}
                    <div className="w-[55%] space-y-4 overflow-y-auto pr-1">
                        {/* Metadata */}
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className="text-xs text-dark-400 mb-1 block">Nombre</label>
                                <input
                                    type="text" className="input h-9 text-sm w-full"
                                    value={test.name}
                                    onChange={e => updateField('name', e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="text-xs text-dark-400 mb-1 block">Categoría</label>
                                <select
                                    className="select h-9 text-sm w-full"
                                    value={test.category}
                                    onChange={e => updateField('category', e.target.value)}
                                >
                                    <option value="provocation">Provocación</option>
                                    <option value="liberation">Liberación</option>
                                    <option value="repositioning">Reposición</option>
                                </select>
                            </div>
                            <div>
                                <label className="text-xs text-dark-400 mb-1 block">Canal</label>
                                <select
                                    className="select h-9 text-sm w-full"
                                    value={test.canal}
                                    onChange={e => updateField('canal', e.target.value)}
                                >
                                    <option value="posterior">Posterior</option>
                                    <option value="lateral">Lateral</option>
                                    <option value="anterior">Anterior</option>
                                </select>
                            </div>
                            <div>
                                <label className="text-xs text-dark-400 mb-1 block">Lado</label>
                                <select
                                    className="select h-9 text-sm w-full"
                                    value={test.side ?? ''}
                                    onChange={e => updateField('side', e.target.value || undefined)}
                                >
                                    <option value="">Sin especificar</option>
                                    <option value="right">Derecho</option>
                                    <option value="left">Izquierdo</option>
                                </select>
                            </div>
                        </div>

                        {/* Phases list */}
                        <div>
                            <h3 className="text-xs font-bold text-dark-500 uppercase tracking-wider mb-2">
                                Fases ({phases.length})
                            </h3>
                            <div className="space-y-1.5">
                                {phases.map((phase, i) => {
                                    const isSelected = i === selectedPhaseIndex
                                    const orient = phase.target_head_orientation ?? { yaw: 0, pitch: 0, roll: 0 }

                                    return (
                                        <div
                                            key={phase.id}
                                            draggable
                                            onDragStart={() => setDragIndex(i)}
                                            onDragOver={e => e.preventDefault()}
                                            onDrop={() => {
                                                if (dragIndex !== null && dragIndex !== i) movePhase(dragIndex, i)
                                                setDragIndex(null)
                                            }}
                                            onDragEnd={() => setDragIndex(null)}
                                            className={`rounded-lg border transition-all ${
                                                isSelected
                                                    ? 'border-orange-500/40 bg-orange-500/5'
                                                    : 'border-dark-700/30 bg-dark-900/30 hover:border-dark-600'
                                            } ${dragIndex === i ? 'opacity-40 scale-95' : ''}`}
                                        >
                                            {/* Compact header — always visible */}
                                            <div
                                                className="flex items-center gap-2 p-2.5 cursor-pointer"
                                                onClick={() => setSelectedPhaseIndex(i)}
                                            >
                                                <div className="cursor-grab active:cursor-grabbing text-dark-500 hover:text-dark-300">
                                                    <GripVertical size={14} />
                                                </div>
                                                <span className="text-xs text-dark-500 w-4 text-center font-mono">{i + 1}</span>
                                                <div className="flex-1 min-w-0">
                                                    <span className="text-sm font-medium text-white truncate block">
                                                        {phase.label}
                                                    </span>
                                                    {!isSelected && (
                                                        <span className="text-[10px] text-dark-500 font-mono">
                                                            {phase.default_duration_seconds}s — Y:{orient.yaw ?? 0} P:{orient.pitch ?? 0} R:{orient.roll ?? 0}
                                                        </span>
                                                    )}
                                                </div>
                                                {isSelected
                                                    ? <ChevronDown size={14} className="text-dark-500 shrink-0" />
                                                    : <ChevronRight size={14} className="text-dark-500 shrink-0" />
                                                }
                                                {phases.length > 1 && (
                                                    <button
                                                        onClick={e => { e.stopPropagation(); removePhase(i) }}
                                                        className="p-1 rounded hover:bg-red-500/20 text-dark-500 hover:text-red-400 transition-colors"
                                                    >
                                                        <Trash2 size={12} />
                                                    </button>
                                                )}
                                            </div>

                                            {/* Expanded detail */}
                                            {isSelected && (
                                                <div className="px-3 pb-3 pt-1 space-y-2.5 border-t border-dark-700/30">
                                                    <div className="grid grid-cols-2 gap-2">
                                                        <div>
                                                            <label className="text-[10px] text-dark-500 mb-0.5 block">Label</label>
                                                            <input
                                                                type="text" className="input h-8 text-sm w-full"
                                                                value={phase.label}
                                                                onChange={e => updatePhase(i, { label: e.target.value })}
                                                            />
                                                        </div>
                                                        <div>
                                                            <label className="text-[10px] text-dark-500 mb-0.5 block">Duración</label>
                                                            <SecondsSpin
                                                                value={phase.default_duration_seconds}
                                                                min={1} max={300}
                                                                onChange={v => updatePhase(i, { default_duration_seconds: v })}
                                                            />
                                                        </div>
                                                        <div>
                                                            <label className="text-[10px] text-dark-500 mb-0.5 block">Posición corporal</label>
                                                            <select
                                                                className="select h-8 text-sm w-full"
                                                                value={phase.body_position ?? 'seated'}
                                                                onChange={e => updatePhase(i, { body_position: e.target.value as BodyPosition })}
                                                            >
                                                                <option value="seated">Sentado</option>
                                                                <option value="supine">Supino</option>
                                                                <option value="prone">Prono</option>
                                                                <option value="side_right">Lateral D</option>
                                                                <option value="side_left">Lateral I</option>
                                                            </select>
                                                        </div>
                                                    </div>
                                                    <div>
                                                        <label className="text-[10px] text-dark-500 mb-0.5 block">Descripción</label>
                                                        <input
                                                            type="text" className="input h-8 text-sm w-full"
                                                            value={phase.description}
                                                            placeholder="Opcional"
                                                            onChange={e => updatePhase(i, { description: e.target.value })}
                                                        />
                                                    </div>
                                                    <div className="space-y-1.5">
                                                        <label className="text-[10px] text-dark-500 block">Orientación</label>
                                                        <OrientationSlider
                                                            label="Yaw" color="text-yellow-400"
                                                            value={orient.yaw ?? 0} min={-180} max={180}
                                                            onChange={v => updatePhaseOrientation(i, 'yaw', v)}
                                                        />
                                                        <OrientationSlider
                                                            label="Pitch" color="text-green-400"
                                                            value={orient.pitch ?? 0} min={-90} max={90}
                                                            onChange={v => updatePhaseOrientation(i, 'pitch', v)}
                                                        />
                                                        <OrientationSlider
                                                            label="Roll" color="text-blue-400"
                                                            value={orient.roll ?? 0} min={-180} max={180}
                                                            onChange={v => updatePhaseOrientation(i, 'roll', v)}
                                                        />
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )
                                })}

                                <button
                                    onClick={addPhase}
                                    className="flex items-center gap-2 w-full p-2.5 rounded-lg border border-dashed border-dark-600 text-dark-400 hover:text-white hover:border-dark-500 transition-colors text-xs"
                                >
                                    <Plus size={14} /> Agregar fase
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* RIGHT — gauges + body + timeline + playback */}
                    <div className="w-[45%] flex flex-col gap-3">
                        {/* Orientation gauges */}
                        <OrientationGauges
                            yaw={currentOrientation.yaw ?? 0}
                            pitch={currentOrientation.pitch ?? 0}
                            roll={currentOrientation.roll ?? 0}
                        />

                        {/* Body position */}
                        <div className="flex items-center justify-center py-1">
                            <BodyPositionIcon position={selectedPhase?.body_position} />
                        </div>

                        {/* Timeline */}
                        <PhaseTimeline
                            phases={phases}
                            selectedIndex={selectedPhaseIndex}
                            onSelectPhase={i => {
                                setSelectedPhaseIndex(i)
                                if (playback.isPlaying) playback.stop()
                            }}
                            playbackProgress={playback.isPlaying ? {
                                phaseIndex: playback.currentPhaseIndex,
                                progress: playback.phaseProgress,
                            } : undefined}
                        />

                        {/* Playback controls */}
                        <div className="flex items-center gap-2">
                            {!playback.isPlaying ? (
                                <button
                                    onClick={() => playback.play(phases, selectedPhaseIndex)}
                                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-orange-500/20 text-orange-400 hover:bg-orange-500/30 transition-colors text-xs font-medium"
                                >
                                    <Play size={14} /> Play
                                </button>
                            ) : (
                                <>
                                    <button
                                        onClick={() => playback.pause()}
                                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-dark-700 text-dark-200 hover:bg-dark-600 transition-colors text-xs font-medium"
                                    >
                                        <Pause size={14} /> Pausa
                                    </button>
                                    <button
                                        onClick={() => playback.stop()}
                                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-dark-700 text-dark-200 hover:bg-dark-600 transition-colors text-xs font-medium"
                                    >
                                        <Square size={14} /> Stop
                                    </button>
                                </>
                            )}
                            <span className="text-[10px] px-2 py-1 rounded font-medium bg-dark-800 text-dark-400 ml-auto">
                                Pos {selectedPhaseIndex + 1}/{phases.length}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    // ════════════════════════════════════════════════════════════════
    // LIST VIEW
    // ════════════════════════════════════════════════════════════════
    const sections = [
        { label: 'Provocación', tests: provocation },
        { label: 'Liberación', tests: liberation },
        { label: 'Reposición', tests: repositioning },
    ]

    return (
        <div className="space-y-6 py-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <p className="text-sm text-dark-300">
                    Seleccione los tests VPPB disponibles en la vista de evaluación.
                </p>
                <div className="flex items-center gap-3">
                    <button
                        onClick={toggleAll}
                        className="text-xs text-siev-400 hover:text-siev-300 transition-colors"
                    >
                        {allEnabled ? 'Desmarcar todos' : 'Marcar todos'}
                    </button>
                    <button
                        onClick={createNewTest}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-orange-500/20 text-orange-400 hover:bg-orange-500/30 transition-colors text-xs font-medium"
                    >
                        <Plus size={14} /> Crear nuevo
                    </button>
                </div>
            </div>

            {/* Sections */}
            {sections.map(section => (
                <div key={section.label}>
                    <h3 className="text-xs font-bold text-dark-500 uppercase tracking-wider mb-3">
                        {section.label}
                    </h3>
                    <div className="space-y-2">
                        {section.tests.map(test => {
                            const enabled = enabledTests.includes(test.id)
                            const sideLabel = test.side === 'right' ? 'D' : test.side === 'left' ? 'I' : ''
                            const isCustom = !isBaseTest(test.id)

                            return (
                                <div
                                    key={test.id}
                                    onClick={() => { setEditingTestId(test.id); setSelectedPhaseIndex(0) }}
                                    className={`flex items-center gap-3 p-3 rounded-lg border transition-all cursor-pointer ${
                                        enabled
                                            ? 'border-orange-500/30 bg-orange-500/5 hover:border-orange-500/50'
                                            : 'border-dark-700/30 bg-dark-900/30 opacity-60 hover:opacity-80'
                                    }`}
                                >
                                    <div onClick={e => e.stopPropagation()}>
                                        <input
                                            type="checkbox"
                                            checked={enabled}
                                            onChange={() => toggleTest(test.id)}
                                            className="rounded border-dark-600 cursor-pointer"
                                        />
                                    </div>
                                    <RotateCcw className="w-4 h-4 text-orange-400 shrink-0" />
                                    <div className="flex-1 min-w-0">
                                        <span className="text-sm font-medium text-white">{test.name}</span>
                                        <span className="text-xs text-dark-400 ml-2">
                                            {test.positions.length} pos • {test.canal} {sideLabel}
                                        </span>
                                    </div>

                                    {/* Actions */}
                                    <div className="flex items-center gap-1 shrink-0" onClick={e => e.stopPropagation()}>
                                        <button
                                            onClick={() => duplicateTest(test)}
                                            className="p-1.5 rounded hover:bg-dark-700 text-dark-500 hover:text-white transition-colors"
                                            title="Duplicar"
                                        >
                                            <Copy size={14} />
                                        </button>
                                        {isCustom && (
                                            <button
                                                onClick={() => deleteTest(test.id)}
                                                className="p-1.5 rounded hover:bg-red-500/20 text-dark-500 hover:text-red-400 transition-colors"
                                                title="Eliminar"
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            ))}

            {/* Bottom create button */}
            <button
                onClick={createNewTest}
                className="flex items-center gap-2 w-full p-3 rounded-lg border border-dashed border-dark-600 text-dark-400 hover:text-white hover:border-dark-500 transition-colors text-sm"
            >
                <Plus size={16} /> Crear prueba posicional
            </button>

            {/* Behavior toggles */}
            <div>
                <h3 className="text-xs font-bold text-dark-500 uppercase tracking-wider mb-3">
                    Comportamiento
                </h3>
                <div className="space-y-2">
                    <div className="flex items-center justify-between p-3 rounded-lg border border-dark-700/30 bg-dark-900/30">
                        <div>
                            <p className="text-sm text-white font-medium">Avance automático</p>
                            <p className="text-xs text-dark-400">Pasar a la siguiente posición cuando el timer llega a 0.</p>
                        </div>
                        <button
                            className={`w-10 h-5 rounded-full transition-colors relative ${timing.auto_advance ? 'bg-siev-500' : 'bg-dark-600'}`}
                            onClick={() => updateConfig('postural.timing.auto_advance', !timing.auto_advance)}
                        >
                            <div className={`w-4 h-4 rounded-full bg-white absolute top-0.5 transition-transform ${timing.auto_advance ? 'translate-x-5' : 'translate-x-0.5'}`} />
                        </button>
                    </div>
                    <div className="flex items-center justify-between p-3 rounded-lg border border-dark-700/30 bg-dark-900/30">
                        <div>
                            <p className="text-sm text-white font-medium">Sonido de cuenta regresiva</p>
                            <p className="text-xs text-dark-400">Beep en los últimos 3 segundos de cada posición.</p>
                        </div>
                        <button
                            className={`w-10 h-5 rounded-full transition-colors relative ${timing.countdown_sound ? 'bg-siev-500' : 'bg-dark-600'}`}
                            onClick={() => updateConfig('postural.timing.countdown_sound', !timing.countdown_sound)}
                        >
                            <div className={`w-4 h-4 rounded-full bg-white absolute top-0.5 transition-transform ${timing.countdown_sound ? 'translate-x-5' : 'translate-x-0.5'}`} />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
