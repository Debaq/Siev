import React from 'react'
import { AppConfig } from '../../../types/config'

interface VisualizationTabProps {
    config: AppConfig
    updateConfig: (path: string, value: any) => void
}

export const VisualizationTab: React.FC<VisualizationTabProps> = ({ config, updateConfig }) => {
    const viz = config.postural?.visualization ?? {
        show_3d_head: true,
        show_target_orientation: true,
        head_model: 'ellipsoid' as const,
    }

    return (
        <div className="space-y-6 py-4">
            <div className="space-y-4">
                <h3 className="text-xs font-bold text-dark-500 uppercase tracking-wider">
                    Visualización 3D
                </h3>

                <div className="flex items-center justify-between p-3 rounded-lg border border-dark-700/30 bg-dark-900/30">
                    <div>
                        <p className="text-sm text-white font-medium">Mostrar cabeza 3D</p>
                        <p className="text-xs text-dark-400">Renderizar modelo 3D de la cabeza con datos IMU.</p>
                    </div>
                    <button
                        className={`w-10 h-5 rounded-full transition-colors relative ${viz.show_3d_head ? 'bg-siev-500' : 'bg-dark-600'}`}
                        onClick={() => updateConfig('postural.visualization.show_3d_head', !viz.show_3d_head)}
                    >
                        <div className={`w-4 h-4 rounded-full bg-white absolute top-0.5 transition-transform ${viz.show_3d_head ? 'translate-x-5' : 'translate-x-0.5'}`} />
                    </button>
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg border border-dark-700/30 bg-dark-900/30">
                    <div>
                        <p className="text-sm text-white font-medium">Mostrar posición objetivo</p>
                        <p className="text-xs text-dark-400">Fantasma semitransparente indicando la orientación esperada.</p>
                    </div>
                    <button
                        className={`w-10 h-5 rounded-full transition-colors relative ${viz.show_target_orientation ? 'bg-siev-500' : 'bg-dark-600'}`}
                        onClick={() => updateConfig('postural.visualization.show_target_orientation', !viz.show_target_orientation)}
                    >
                        <div className={`w-4 h-4 rounded-full bg-white absolute top-0.5 transition-transform ${viz.show_target_orientation ? 'translate-x-5' : 'translate-x-0.5'}`} />
                    </button>
                </div>

                <div className="p-3 rounded-lg border border-dark-700/30 bg-dark-900/30">
                    <div className="flex items-center justify-between mb-2">
                        <div>
                            <p className="text-sm text-white font-medium">Modelo de cabeza</p>
                            <p className="text-xs text-dark-400">Forma geométrica del modelo 3D.</p>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        {(['ellipsoid', 'capsule'] as const).map(model => (
                            <button
                                key={model}
                                onClick={() => updateConfig('postural.visualization.head_model', model)}
                                className={`flex-1 px-3 py-2 rounded-lg border text-sm font-medium transition-all ${
                                    viz.head_model === model
                                        ? 'border-siev-500/50 bg-siev-500/10 text-siev-400'
                                        : 'border-dark-700/30 bg-dark-900/20 text-dark-400 hover:text-white hover:border-dark-600'
                                }`}
                            >
                                {model === 'ellipsoid' ? 'Elipsoide' : 'Cápsula'}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}
