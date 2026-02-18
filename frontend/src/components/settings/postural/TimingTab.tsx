import React from 'react'
import { AppConfig } from '../../../types/config'
import { ALL_VPPB_TESTS } from '../../../data/vppbTests'

interface TimingTabProps {
    config: AppConfig
    updateConfig: (path: string, value: any) => void
}

export const TimingTab: React.FC<TimingTabProps> = ({ config, updateConfig }) => {
    const timing = config.postural?.timing ?? { position_durations: {}, auto_advance: false, countdown_sound: true }

    const handleDurationChange = (positionId: string, value: number) => {
        const newDurations = { ...timing.position_durations, [positionId]: value }
        updateConfig('postural.timing.position_durations', newDurations)
    }

    // Get all unique positions across all tests
    const allPositions = new Map<string, { label: string; defaultDuration: number; testNames: string[] }>()
    for (const test of ALL_VPPB_TESTS) {
        for (const pos of test.positions) {
            const existing = allPositions.get(pos.id)
            if (existing) {
                if (!existing.testNames.includes(test.name)) {
                    existing.testNames.push(test.name)
                }
            } else {
                allPositions.set(pos.id, {
                    label: pos.label,
                    defaultDuration: pos.default_duration_seconds,
                    testNames: [test.name],
                })
            }
        }
    }

    return (
        <div className="space-y-6 py-4">
            {/* Global settings */}
            <div className="space-y-4">
                <h3 className="text-xs font-bold text-dark-500 uppercase tracking-wider">
                    Comportamiento
                </h3>

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

            {/* Per-position duration overrides */}
            <div>
                <h3 className="text-xs font-bold text-dark-500 uppercase tracking-wider mb-3">
                    Duración por posición (segundos)
                </h3>
                <p className="text-xs text-dark-400 mb-3">
                    Deje vacío para usar la duración predeterminada.
                </p>

                <div className="space-y-1.5">
                    {Array.from(allPositions.entries()).map(([posId, meta]) => {
                        const override = timing.position_durations[posId]
                        return (
                            <div
                                key={posId}
                                className="flex items-center gap-3 p-2.5 rounded-lg border border-dark-700/30 bg-dark-900/20"
                            >
                                <div className="flex-1 min-w-0">
                                    <span className="text-sm text-white font-medium">{meta.label}</span>
                                    <span className="text-[10px] text-dark-500 ml-2">(def: {meta.defaultDuration}s)</span>
                                </div>
                                <input
                                    type="number"
                                    className="input h-8 w-20 text-sm text-center font-mono"
                                    placeholder={String(meta.defaultDuration)}
                                    value={override ?? ''}
                                    min={1}
                                    max={300}
                                    onChange={(e) => {
                                        const val = e.target.value
                                        if (val === '') {
                                            const newDurations = { ...timing.position_durations }
                                            delete newDurations[posId]
                                            updateConfig('postural.timing.position_durations', newDurations)
                                        } else {
                                            handleDurationChange(posId, Number(val))
                                        }
                                    }}
                                />
                            </div>
                        )
                    })}
                </div>
            </div>
        </div>
    )
}
