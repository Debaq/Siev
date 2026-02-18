import React, { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { AppConfig, SubjectiveSymptomDefinition } from '../../../types/config'

interface SymptomsTabProps {
    config: AppConfig
    updateConfig: (path: string, value: any) => void
}

const BASE_SYMPTOM_IDS = ['vertigo', 'nausea', 'vomito']

export const SymptomsTab: React.FC<SymptomsTabProps> = ({ config, updateConfig }) => {
    const symptomsConfig = config.postural?.symptoms
    const scaleType = symptomsConfig?.scale?.type ?? 'vas_0_10'
    const symptoms: SubjectiveSymptomDefinition[] = symptomsConfig?.symptoms ?? []

    const [newLabel, setNewLabel] = useState('')

    const handleScaleChange = (type: 'vas_0_10' | 'likert_0_4') => {
        updateConfig('postural.symptoms.scale.type', type)
    }

    const toggleSymptom = (id: string) => {
        const updated = symptoms.map(s =>
            s.id === id ? { ...s, enabled: !s.enabled } : s
        )
        updateConfig('postural.symptoms.symptoms', updated)
    }

    const removeSymptom = (id: string) => {
        const updated = symptoms.filter(s => s.id !== id)
        updateConfig('postural.symptoms.symptoms', updated)
    }

    const addSymptom = () => {
        const label = newLabel.trim()
        if (!label) return
        const id = label.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')
        if (symptoms.some(s => s.id === id)) return
        const updated = [...symptoms, { id, label, enabled: true }]
        updateConfig('postural.symptoms.symptoms', updated)
        setNewLabel('')
    }

    return (
        <div className="space-y-6 py-4">
            {/* Scale type */}
            <div>
                <h3 className="text-xs font-bold text-dark-500 uppercase tracking-wider mb-3">
                    Tipo de escala
                </h3>
                <p className="text-sm text-dark-400 mb-3">
                    Escala utilizada para registrar la intensidad de s&iacute;ntomas subjetivos durante pruebas de provocaci&oacute;n.
                </p>
                <div className="flex rounded-lg overflow-hidden border border-dark-700">
                    <button
                        onClick={() => handleScaleChange('vas_0_10')}
                        className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
                            scaleType === 'vas_0_10'
                                ? 'bg-orange-500/20 text-orange-400 border-r border-orange-500/30'
                                : 'bg-dark-800 text-dark-400 hover:text-dark-200 border-r border-dark-700'
                        }`}
                    >
                        VAS 0-10
                    </button>
                    <button
                        onClick={() => handleScaleChange('likert_0_4')}
                        className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
                            scaleType === 'likert_0_4'
                                ? 'bg-orange-500/20 text-orange-400'
                                : 'bg-dark-800 text-dark-400 hover:text-dark-200'
                        }`}
                    >
                        Likert 0-4
                    </button>
                </div>
            </div>

            {/* Symptoms list */}
            <div>
                <h3 className="text-xs font-bold text-dark-500 uppercase tracking-wider mb-3">
                    S&iacute;ntomas registrados
                </h3>
                <div className="space-y-2">
                    {symptoms.map(symptom => {
                        const isBase = BASE_SYMPTOM_IDS.includes(symptom.id)
                        return (
                            <div
                                key={symptom.id}
                                className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${
                                    symptom.enabled
                                        ? 'border-orange-500/30 bg-orange-500/5'
                                        : 'border-dark-700/30 bg-dark-900/30 opacity-60'
                                }`}
                            >
                                <input
                                    type="checkbox"
                                    checked={symptom.enabled}
                                    onChange={() => toggleSymptom(symptom.id)}
                                    className="rounded border-dark-600"
                                />
                                <span className="text-sm font-medium text-white flex-1">{symptom.label}</span>
                                {isBase ? (
                                    <span className="text-[9px] text-dark-600 uppercase">base</span>
                                ) : (
                                    <button
                                        onClick={() => removeSymptom(symptom.id)}
                                        className="p-1 hover:bg-red-500/20 rounded text-dark-500 hover:text-red-400 transition-colors"
                                    >
                                        <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                )}
                            </div>
                        )
                    })}
                </div>
            </div>

            {/* Add custom symptom */}
            <div>
                <h3 className="text-xs font-bold text-dark-500 uppercase tracking-wider mb-3">
                    Agregar s&iacute;ntoma
                </h3>
                <div className="flex gap-2">
                    <input
                        type="text"
                        className="input flex-1 h-9 text-sm"
                        placeholder="Nombre del s&iacute;ntoma..."
                        value={newLabel}
                        onChange={(e) => setNewLabel(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && addSymptom()}
                    />
                    <button
                        onClick={addSymptom}
                        disabled={!newLabel.trim()}
                        className="btn btn-primary h-9 px-3 text-sm disabled:opacity-40"
                    >
                        <Plus className="w-4 h-4" />
                        Agregar
                    </button>
                </div>
            </div>
        </div>
    )
}
