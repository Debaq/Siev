import React, { useState, useCallback } from 'react';
import {
    Eye, Target, MoveHorizontal, Activity, RotateCcw, Thermometer, PlayCircle,
    LucideIcon, ChevronDown, ChevronRight, Copy, Trash2, Plus, GripVertical,
    Shield, ArrowLeft
} from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsField } from '../shared/SettingsField';
import { AppConfig, CaloricProtocol, CaloricIrrigation } from '../../../types/config';

interface TestsTabProps {
    config: AppConfig;
    updateConfig: (path: string, value: any) => void;
}

interface TestDefinition {
    id: string;
    title: string;
    description: string;
    icon: LucideIcon;
    color: string;
    bg: string;
    border: string;
    hasConfig: boolean;
}

const VNG_TESTS: TestDefinition[] = [
    {
        id: 'spontaneous',
        title: 'Nistagmo Espontáneo',
        description: 'Evaluación de nistagmo sin fijación visual.',
        icon: Eye,
        color: 'text-blue-400',
        bg: 'bg-blue-500/10',
        border: 'border-blue-500/20',
        hasConfig: false,
    },
    {
        id: 'calibration_gaze',
        title: 'Calibración Ocular',
        description: 'Secuencia de puntos para calibrar el seguimiento.',
        icon: Target,
        color: 'text-pink-400',
        bg: 'bg-pink-500/10',
        border: 'border-pink-500/20',
        hasConfig: false,
    },
    {
        id: 'saccades',
        title: 'Sacadas',
        description: 'Aleatorias, fijas y anti-sacadas.',
        icon: MoveHorizontal,
        color: 'text-green-400',
        bg: 'bg-green-500/10',
        border: 'border-green-500/20',
        hasConfig: false,
    },
    {
        id: 'pursuit',
        title: 'Seguimiento Pendular',
        description: 'Sinusoidal, suma de senos y step-ramp.',
        icon: Activity,
        color: 'text-purple-400',
        bg: 'bg-purple-500/10',
        border: 'border-purple-500/20',
        hasConfig: false,
    },
    {
        id: 'positional',
        title: 'Pruebas Posicionales',
        description: 'Dix-Hallpike y cambios posturales (Mirada).',
        icon: RotateCcw,
        color: 'text-orange-400',
        bg: 'bg-orange-500/10',
        border: 'border-orange-500/20',
        hasConfig: false,
    },
    {
        id: 'caloric',
        title: 'Pruebas Calóricas',
        description: 'Estimulación térmica del oído interno.',
        icon: Thermometer,
        color: 'text-red-400',
        bg: 'bg-red-500/10',
        border: 'border-red-500/20',
        hasConfig: true,
    },
    {
        id: 'optokinetic',
        title: 'Optocinético / Full Field',
        description: 'Barras, damero y movimiento visual completo.',
        icon: PlayCircle,
        color: 'text-cyan-400',
        bg: 'bg-cyan-500/10',
        border: 'border-cyan-500/20',
        hasConfig: false,
    },
];

const generateId = () => `protocol-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

// ── Spin input for seconds ──────────────────────────────────────────
const SecondsSpin: React.FC<{
    value: number;
    onChange: (v: number) => void;
    min?: number;
    max?: number;
    step?: number;
    label?: string;
}> = ({ value, onChange, min = 0, max = 600, step = 1, label }) => (
    <div className="flex items-center gap-2">
        <input
            type="number"
            className="input h-8 w-20 text-sm text-center font-mono"
            value={value}
            min={min}
            max={max}
            step={step}
            onChange={e => {
                const v = Number(e.target.value);
                if (!isNaN(v) && v >= min && v <= max) onChange(v);
            }}
        />
        <span className="text-xs text-dark-500">{label ?? 's'}</span>
    </div>
);

// ── Timeline visualization ──────────────────────────────────────────
const Timeline: React.FC<{ protocol: CaloricProtocol }> = ({ protocol }) => {
    const { timing } = protocol;
    const total = timing.total_duration;
    if (total <= 0) return null;

    const pct = (v: number) => Math.min((v / total) * 100, 100);
    const clampEnd = (start: number, dur: number) => Math.min(start + dur, total);

    const torokStart = pct(timing.torok.start_time);
    const torokWidth = pct(clampEnd(timing.torok.start_time, timing.torok.duration)) - torokStart;
    const ofiStart = pct(timing.ofi.start_time);
    const ofiWidth = pct(clampEnd(timing.ofi.start_time, timing.ofi.duration)) - ofiStart;
    const delayWidth = pct(timing.delay);

    // Tick marks every 30s
    const ticks: number[] = [];
    for (let t = 0; t <= total; t += 30) ticks.push(t);
    if (ticks[ticks.length - 1] !== total) ticks.push(total);

    return (
        <div className="space-y-1.5">
            <div className="flex items-center gap-4 text-[10px] text-dark-400">
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-dark-600 inline-block" /> Delay</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-orange-500/60 inline-block" /> Irrigación</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-sky-500/60 inline-block" /> Torok</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-amber-500/60 inline-block" /> OFI</span>
                <span className="ml-auto font-mono">{total}s total</span>
            </div>
            <div className="relative h-7 bg-dark-900 rounded-md border border-dark-700/50 overflow-hidden">
                {/* Delay */}
                {timing.delay > 0 && (
                    <div
                        className="absolute top-0 bottom-0 bg-dark-600"
                        style={{ left: '0%', width: `${delayWidth}%` }}
                    />
                )}
                {/* Irrigation */}
                {(timing.irrigation_duration ?? 0) > 0 && (
                    <div
                        className="absolute top-0 bottom-0 bg-orange-500/40 border-x border-orange-400/50"
                        style={{ left: '0%', width: `${pct(timing.irrigation_duration)}%` }}
                    />
                )}
                {/* Torok */}
                {timing.torok.duration > 0 && (
                    <div
                        className="absolute top-0 bottom-0 bg-sky-500/40 border-x border-sky-400/50"
                        style={{ left: `${torokStart}%`, width: `${torokWidth}%` }}
                    />
                )}
                {/* OFI */}
                {timing.ofi.duration > 0 && (
                    <div
                        className="absolute top-0 bottom-0 bg-amber-500/40 border-x border-amber-400/50"
                        style={{ left: `${ofiStart}%`, width: `${ofiWidth}%` }}
                    />
                )}
            </div>
            {/* Tick labels */}
            <div className="relative h-3">
                {ticks.map(t => (
                    <span
                        key={t}
                        className="absolute text-[9px] text-dark-500 font-mono -translate-x-1/2"
                        style={{ left: `${pct(t)}%` }}
                    >
                        {t}
                    </span>
                ))}
            </div>
        </div>
    );
};

// ── Mini timeline for cards ─────────────────────────────────────────
const MiniTimeline: React.FC<{ protocol: CaloricProtocol }> = ({ protocol }) => {
    const { timing } = protocol;
    const total = timing.total_duration;
    if (total <= 0) return null;

    const pct = (v: number) => Math.min((v / total) * 100, 100);
    const clampEnd = (start: number, dur: number) => Math.min(start + dur, total);

    const torokStart = pct(timing.torok.start_time);
    const torokWidth = pct(clampEnd(timing.torok.start_time, timing.torok.duration)) - torokStart;
    const ofiStart = pct(timing.ofi.start_time);
    const ofiWidth = pct(clampEnd(timing.ofi.start_time, timing.ofi.duration)) - ofiStart;

    const irrigationDur = timing.irrigation_duration ?? 0;
    const irrigationWidth = pct(irrigationDur);

    return (
        <div className="relative h-2 bg-dark-900/60 rounded-full overflow-hidden w-full">
            {irrigationDur > 0 && (
                <div
                    className="absolute top-0 bottom-0 bg-orange-500/50 rounded-full"
                    style={{ left: '0%', width: `${irrigationWidth}%` }}
                />
            )}
            {timing.torok.duration > 0 && (
                <div
                    className="absolute top-0 bottom-0 bg-sky-500/50 rounded-full"
                    style={{ left: `${torokStart}%`, width: `${torokWidth}%` }}
                />
            )}
            {timing.ofi.duration > 0 && (
                <div
                    className="absolute top-0 bottom-0 bg-amber-500/50 rounded-full"
                    style={{ left: `${ofiStart}%`, width: `${ofiWidth}%` }}
                />
            )}
        </div>
    );
};

// ════════════════════════════════════════════════════════════════════
export const TestsTab: React.FC<TestsTabProps> = ({ config, updateConfig }) => {
    const [expandedTest, setExpandedTest] = useState<string | null>(null);
    const [editingProtocolId, setEditingProtocolId] = useState<string | null>(null);
    const [dragIndex, setDragIndex] = useState<number | null>(null);

    const protocols = config.vng.tests?.caloric?.protocols ?? [];

    const toggleTest = (id: string) => {
        setExpandedTest(prev => prev === id ? null : id);
    };

    // ── Protocol CRUD ────────────────────────────────────────────
    const updateProtocols = useCallback((newProtocols: CaloricProtocol[]) => {
        updateConfig('vng.tests.caloric.protocols', newProtocols);
    }, [updateConfig]);

    const updateProtocol = useCallback((index: number, updated: CaloricProtocol) => {
        const newProtocols = [...protocols];
        newProtocols[index] = updated;
        updateProtocols(newProtocols);
    }, [protocols, updateProtocols]);

    const duplicateProtocol = (index: number) => {
        const source = protocols[index];
        const copy: CaloricProtocol = {
            ...JSON.parse(JSON.stringify(source)),
            id: generateId(),
            name: `${source.name} (copia)`,
            is_base: false,
        };
        const newProtocols = [...protocols];
        newProtocols.splice(index + 1, 0, copy);
        updateProtocols(newProtocols);
    };

    const deleteProtocol = (index: number) => {
        if (protocols[index].is_base) return;
        if (editingProtocolId === protocols[index].id) setEditingProtocolId(null);
        updateProtocols(protocols.filter((_, i) => i !== index));
    };

    // ── Irrigation helpers ───────────────────────────────────────
    const addIrrigation = (pIdx: number) => {
        const p = protocols[pIdx];
        const irr: CaloricIrrigation = { label: '37°C OD', temperature: 37, ear: 'od' };
        updateProtocol(pIdx, { ...p, irrigations: [...p.irrigations, irr] });
    };

    const removeIrrigation = (pIdx: number, iIdx: number) => {
        const p = protocols[pIdx];
        updateProtocol(pIdx, { ...p, irrigations: p.irrigations.filter((_, i) => i !== iIdx) });
    };

    const updateIrrigation = (pIdx: number, iIdx: number, field: keyof CaloricIrrigation, value: any) => {
        const p = protocols[pIdx];
        const list = [...p.irrigations];
        const irr = { ...list[iIdx], [field]: value };
        irr.label = `${irr.temperature}°C ${irr.ear === 'od' ? 'OD' : 'OI'}`;
        list[iIdx] = irr;
        updateProtocol(pIdx, { ...p, irrigations: list });
    };

    const moveIrrigation = (pIdx: number, from: number, to: number) => {
        if (to < 0 || to >= protocols[pIdx].irrigations.length) return;
        const p = protocols[pIdx];
        const list = [...p.irrigations];
        const [moved] = list.splice(from, 1);
        list.splice(to, 0, moved);
        updateProtocol(pIdx, { ...p, irrigations: list });
    };

    // ── Find editing protocol ────────────────────────────────────
    const editingIndex = editingProtocolId ? protocols.findIndex(p => p.id === editingProtocolId) : -1;
    const editingProtocol = editingIndex >= 0 ? protocols[editingIndex] : null;

    // ════════════════════════════════════════════════════════════
    // DETAIL VIEW — editing a single protocol
    // ════════════════════════════════════════════════════════════
    if (editingProtocol && editingIndex >= 0) {
        const pIdx = editingIndex;
        const protocol = editingProtocol;

        const setTiming = (patch: Record<string, any>) =>
            updateProtocol(pIdx, { ...protocol, timing: { ...protocol.timing, ...patch } });

        return (
            <div className="space-y-6 py-4 animate-fade-in">
                {/* Back button */}
                <button
                    onClick={() => setEditingProtocolId(null)}
                    className="flex items-center gap-2 text-sm text-dark-300 hover:text-white transition-colors"
                >
                    <ArrowLeft size={16} />
                    Volver a protocolos
                </button>

                {/* Header */}
                <div className="flex items-center gap-3">
                    <Thermometer size={20} className="text-red-400" />
                    <h2 className="text-lg font-bold text-white">{protocol.name}</h2>
                    {protocol.is_base && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium bg-amber-500/15 text-amber-400 rounded border border-amber-500/20">
                            <Shield size={10} /> Base
                        </span>
                    )}
                </div>

                {/* Name + comment */}
                <div className="grid grid-cols-2 gap-4">
                    <SettingsField label="Nombre">
                        <input
                            type="text"
                            className="input h-9 text-sm"
                            value={protocol.name}
                            onChange={e => updateProtocol(pIdx, { ...protocol, name: e.target.value })}
                        />
                    </SettingsField>
                    <SettingsField label="Comentario">
                        <input
                            type="text"
                            className="input h-9 text-sm"
                            value={protocol.comment}
                            placeholder="Opcional"
                            onChange={e => updateProtocol(pIdx, { ...protocol, comment: e.target.value })}
                        />
                    </SettingsField>
                </div>

                {/* Timeline preview */}
                <SettingsSection title="Vista previa" description="Línea de tiempo de cada irrigación.">
                    <Timeline protocol={protocol} />
                </SettingsSection>

                {/* Irrigations */}
                <SettingsSection
                    title="Irrigaciones"
                    description="Arrastrá para reordenar la secuencia."
                >
                    <div className="space-y-2">
                        {protocol.irrigations.map((irr, iIdx) => (
                            <div
                                key={iIdx}
                                draggable
                                onDragStart={() => setDragIndex(iIdx)}
                                onDragOver={e => e.preventDefault()}
                                onDrop={() => {
                                    if (dragIndex !== null && dragIndex !== iIdx) {
                                        moveIrrigation(pIdx, dragIndex, iIdx);
                                    }
                                    setDragIndex(null);
                                }}
                                onDragEnd={() => setDragIndex(null)}
                                className={`flex items-center gap-3 p-2.5 rounded-lg border border-dark-700/30 bg-dark-900/30
                                    ${dragIndex === iIdx ? 'opacity-40 scale-95' : 'hover:border-dark-600'} transition-all`}
                            >
                                <div className="cursor-grab active:cursor-grabbing text-dark-500 hover:text-dark-300">
                                    <GripVertical size={14} />
                                </div>
                                <span className="text-xs text-dark-500 w-4 text-center font-mono">
                                    {iIdx + 1}
                                </span>
                                <input
                                    type="number"
                                    className="input h-8 w-20 text-sm text-center font-mono"
                                    value={irr.temperature}
                                    min={0}
                                    max={60}
                                    onChange={e => updateIrrigation(pIdx, iIdx, 'temperature', Number(e.target.value))}
                                />
                                <span className="text-xs text-dark-400">°C</span>
                                <select
                                    className="select h-8 text-sm w-20"
                                    value={irr.ear}
                                    onChange={e => updateIrrigation(pIdx, iIdx, 'ear', e.target.value)}
                                >
                                    <option value="od">OD</option>
                                    <option value="oi">OI</option>
                                </select>
                                <span className="flex-1 text-xs text-dark-400 truncate font-medium">
                                    {irr.label}
                                </span>
                                <button
                                    onClick={() => removeIrrigation(pIdx, iIdx)}
                                    className="p-1.5 rounded hover:bg-red-500/20 text-dark-500 hover:text-red-400 transition-colors"
                                    title="Quitar"
                                >
                                    <Trash2 size={13} />
                                </button>
                            </div>
                        ))}
                        <button
                            onClick={() => addIrrigation(pIdx)}
                            className="flex items-center gap-2 w-full p-2.5 rounded-lg border border-dashed border-dark-600 text-dark-400 hover:text-white hover:border-dark-500 transition-colors text-xs"
                        >
                            <Plus size={14} />
                            Agregar irrigación
                        </button>
                    </div>
                </SettingsSection>

                {/* Timing */}
                <SettingsSection title="Temporización" description="Tiempos en segundos para cada irrigación.">
                    <div className="grid grid-cols-2 gap-4">
                        <SettingsField label="Delay inicial" description="Espera antes de grabar.">
                            <SecondsSpin value={protocol.timing.delay} min={0} max={60} onChange={v => setTiming({ delay: v })} />
                        </SettingsField>
                        <SettingsField label="Duración de irrigación" description="Tiempo de irrigación tras el delay.">
                            <SecondsSpin value={protocol.timing.irrigation_duration ?? 0} min={0} max={120} onChange={v => setTiming({ irrigation_duration: v })} />
                        </SettingsField>
                        <SettingsField label="Descanso entre irrigaciones" description="Pausa entre cada irrigación.">
                            <SecondsSpin value={protocol.timing.rest_time} min={0} max={600} onChange={v => setTiming({ rest_time: v })} />
                        </SettingsField>
                        <SettingsField label="Duración total de registro" description="Duración total de cada registro.">
                            <SecondsSpin value={protocol.timing.total_duration} min={10} max={300} step={10} onChange={v => setTiming({ total_duration: v })} />
                        </SettingsField>
                    </div>
                </SettingsSection>

                {/* Torok */}
                <SettingsSection title="Torok" description="Ventana de evaluación de Torok.">
                    <div className="grid grid-cols-2 gap-4">
                        <SettingsField label="Inicio" description="Segundo de inicio.">
                            <SecondsSpin
                                value={protocol.timing.torok.start_time} min={0} max={protocol.timing.total_duration}
                                onChange={v => setTiming({ torok: { ...protocol.timing.torok, start_time: v } })}
                            />
                        </SettingsField>
                        <SettingsField label="Duración" description="Duración de evaluación.">
                            <SecondsSpin
                                value={protocol.timing.torok.duration} min={1} max={120}
                                onChange={v => setTiming({ torok: { ...protocol.timing.torok, duration: v } })}
                            />
                        </SettingsField>
                    </div>
                </SettingsSection>

                {/* OFI */}
                <SettingsSection title="OFI (Índice de Fijación Ocular)" description="Ventana de fijación con LED.">
                    <div className="grid grid-cols-3 gap-4">
                        <SettingsField label="Inicio" description="Segundo de activación.">
                            <SecondsSpin
                                value={protocol.timing.ofi.start_time} min={0} max={protocol.timing.total_duration}
                                onChange={v => setTiming({ ofi: { ...protocol.timing.ofi, start_time: v } })}
                            />
                        </SettingsField>
                        <SettingsField label="Duración" description="Tiempo activo.">
                            <SecondsSpin
                                value={protocol.timing.ofi.duration} min={1} max={60}
                                onChange={v => setTiming({ ofi: { ...protocol.timing.ofi, duration: v } })}
                            />
                        </SettingsField>
                        <SettingsField label="LED de fijación" description="Qué LED encender.">
                            <select
                                className="select h-8 text-sm"
                                value={protocol.timing.ofi.fixation_led}
                                onChange={e => setTiming({
                                    ofi: { ...protocol.timing.ofi, fixation_led: e.target.value as 'right' | 'left' | 'both' }
                                })}
                            >
                                <option value="right">Derecho</option>
                                <option value="left">Izquierdo</option>
                                <option value="both">Ambos</option>
                            </select>
                        </SettingsField>
                    </div>
                </SettingsSection>
            </div>
        );
    }

    // ════════════════════════════════════════════════════════════
    // LIST VIEW — tests + protocol cards
    // ════════════════════════════════════════════════════════════
    return (
        <div className="space-y-4 py-4">
            <div className="space-y-2">
                {VNG_TESTS.map((test) => {
                    const Icon = test.icon;
                    const isExpanded = expandedTest === test.id;

                    return (
                        <div key={test.id}>
                            <button
                                onClick={() => test.hasConfig && toggleTest(test.id)}
                                className={`w-full flex items-center gap-3 p-4 rounded-lg border ${test.border} ${test.bg}
                                    ${test.hasConfig ? 'hover:brightness-125 cursor-pointer' : 'opacity-60 cursor-default'}
                                    transition-all duration-150 text-left`}
                            >
                                <div className={`mt-0.5 ${test.color}`}>
                                    <Icon size={22} />
                                </div>
                                <div className="min-w-0 flex-1">
                                    <h3 className="text-sm font-semibold text-white">{test.title}</h3>
                                    <p className="text-xs text-dark-300 mt-0.5">{test.description}</p>
                                </div>
                                {test.hasConfig && (
                                    <div className="text-dark-400">
                                        {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                    </div>
                                )}
                                {!test.hasConfig && (
                                    <span className="text-[10px] text-dark-500 italic">Próximamente</span>
                                )}
                            </button>

                            {/* Protocol cards */}
                            {test.id === 'caloric' && isExpanded && (
                                <div className="mt-3 ml-4 mr-1 grid grid-cols-1 gap-3 animate-fade-in">
                                    {protocols.map((protocol, pIdx) => (
                                        <div
                                            key={protocol.id}
                                            onClick={() => setEditingProtocolId(protocol.id)}
                                            className="group rounded-lg border border-dark-700/50 bg-dark-800/50 p-4 cursor-pointer
                                                hover:border-red-500/30 hover:bg-dark-800/80 transition-all"
                                        >
                                            <div className="flex items-start gap-3">
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-sm font-semibold text-white group-hover:text-red-300 transition-colors truncate">
                                                            {protocol.name}
                                                        </span>
                                                        {protocol.is_base && (
                                                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium bg-amber-500/15 text-amber-400 rounded border border-amber-500/20 shrink-0">
                                                                <Shield size={9} /> Base
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="flex items-center gap-3 text-xs text-dark-400 mb-2.5">
                                                        <span>{protocol.irrigations.length} irrigación{protocol.irrigations.length !== 1 ? 'es' : ''}</span>
                                                        <span className="text-dark-600">|</span>
                                                        <span>{protocol.irrigations.map(i => i.label).join(' → ')}</span>
                                                    </div>
                                                    <MiniTimeline protocol={protocol} />
                                                </div>
                                                <div className="flex items-center gap-1 shrink-0" onClick={e => e.stopPropagation()}>
                                                    <button
                                                        onClick={() => duplicateProtocol(pIdx)}
                                                        className="p-1.5 rounded hover:bg-dark-700 text-dark-500 hover:text-white transition-colors"
                                                        title="Duplicar"
                                                    >
                                                        <Copy size={14} />
                                                    </button>
                                                    {!protocol.is_base && (
                                                        <button
                                                            onClick={() => deleteProtocol(pIdx)}
                                                            className="p-1.5 rounded hover:bg-red-500/20 text-dark-500 hover:text-red-400 transition-colors"
                                                            title="Eliminar"
                                                        >
                                                            <Trash2 size={14} />
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};
