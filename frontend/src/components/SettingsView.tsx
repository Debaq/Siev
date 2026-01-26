import React, { useState } from 'react';
import { Settings, Save, RotateCcw, FileText, Activity, Monitor, LayoutGrid } from 'lucide-react';
import { useSettingsConfig } from '../hooks/useSettingsConfig';
import { ModuleSelector, ModuleDefinition } from './settings/ModuleSelector';
import { GeneralSettings } from './settings/general';
import { VNGSettings } from './settings/vng';
import { useWebSocket } from '../contexts/WebSocketContext';

import { StimulusScreenSettings } from './settings/stimulus/StimulusScreenSettings';

const MODULE_LIST: ModuleDefinition[] = [
    { 
        id: 'general', 
        label: 'SISTEMA', 
        name: 'General', 
        icon: FileText, 
        color: 'text-blue-400', 
        description: 'Institución, equipo, almacenamiento y módulos.',
        isAlwaysVisible: true 
    },
    { 
        id: 'vng', 
        label: 'VNG', 
        name: 'Video-Oculografía', 
        icon: Activity, 
        imagePath: '/mod_vng.png',
        color: 'text-cyan-400', 
        description: 'Análisis de nistagmo y movimientos oculares por video.' 
    },
    { 
        id: 'stimulus_screen', 
        label: 'VISUAL', 
        name: 'Pantalla de Estímulos', 
        icon: Monitor, 
        imagePath: '/mod_stimulus.png',
        color: 'text-purple-400', 
        description: 'Control de optotipos y estímulos en monitor secundario.' 
    },
    { 
        id: 'vhit', 
        label: 'vHIT', 
        name: 'Video Head Impulse', 
        icon: Activity, 
        imagePath: '/mod_vhit.png',
        color: 'text-orange-400', 
        description: 'Prueba de impulso cefálico asistida por video.' 
    },
    { 
        id: 'static_posturography', 
        label: 'PLAT', 
        name: 'Posturografía Estática', 
        icon: LayoutGrid, 
        imagePath: '/mod_posturography.png',
        color: 'text-green-400', 
        description: 'Análisis de equilibrio en plataforma de fuerza SIEV.' 
    },
    { 
        id: 'imu_posturography', 
        label: 'IMU', 
        name: 'Posturografía Inercial', 
        icon: Activity, 
        imagePath: '/mod_imu.png',
        color: 'text-emerald-400', 
        description: 'Evaluación de balance mediante sensores corporales.' 
    },
];

const SettingsView: React.FC = () => {
    const { send } = useWebSocket();
    const { 
        config, 
        isLoading, 
        isSaving, 
        isDirty, 
        updateConfig, 
        saveConfig, 
        resetConfig 
    } = useSettingsConfig(send);

    const [activeModuleId, setActiveModuleId] = useState('general');

    if (isLoading || !config) {
        return (
            <div className="h-full flex items-center justify-center bg-dark-950">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-siev-500/20 border-t-siev-500 rounded-full animate-spin" />
                    <p className="text-dark-400 animate-pulse">Cargando configuración...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col bg-dark-950 text-dark-100 overflow-hidden relative">
            {/* Header */}
            <header className="px-6 pt-4 pb-2 border-b border-dark-800 shrink-0">
                <div className="flex justify-between items-center mb-3">
                    <div>
                        <h2 className="text-xl font-bold text-white flex items-center gap-2">
                            <Settings className="w-5 h-5 text-siev-500" />
                            Configuración
                        </h2>
                        <p className="text-xs text-dark-500 mt-0.5">Gestione el ecosistema SIEV y sus periféricos.</p>
                    </div>

                    <div className="flex items-center gap-4">
                        {isSaving ? (
                            <div className="flex items-center gap-2 text-xs text-siev-400 bg-siev-500/10 px-3 py-1.5 rounded-full border border-siev-500/20">
                                <div className="w-3 h-3 border-2 border-siev-500/20 border-t-siev-500 rounded-full animate-spin" />
                                <span className="font-medium">Guardando...</span>
                            </div>
                        ) : isDirty ? (
                            <div className="flex items-center gap-2 text-xs text-yellow-500 bg-yellow-500/10 px-3 py-1.5 rounded-full border border-yellow-500/20">
                                <button onClick={() => resetConfig()} className="hover:text-white transition-colors">
                                    <RotateCcw className="w-3 h-3 animate-spin-slow" />
                                </button>
                                <span className="font-medium">Cambios pendientes...</span>
                                <button 
                                    onClick={() => saveConfig()}
                                    className="ml-2 bg-siev-600 hover:bg-siev-500 text-white px-2 py-0.5 rounded text-[10px] transition-colors"
                                >
                                    Guardar Ahora
                                </button>
                            </div>
                        ) : (
                            <div className="flex items-center gap-2 text-xs text-dark-500 bg-dark-800/50 px-3 py-1.5 rounded-full border border-dark-700">
                                <Save className="w-3 h-3" />
                                <span className="font-medium">Configuración guardada</span>
                            </div>
                        )}
                    </div>
                </div>

                <ModuleSelector 
                    modules={MODULE_LIST}
                    activeModuleId={activeModuleId}
                    onModuleSelect={setActiveModuleId}
                    activeStates={config.modules}
                />
            </header>

            {/* Main Content */}
            <main className="flex-1 overflow-hidden px-6 py-2">
                <div className="max-w-5xl mx-auto h-full flex flex-col">
                    {activeModuleId === 'general' && (
                        <GeneralSettings config={config} updateConfig={updateConfig} />
                    )}
                    {activeModuleId === 'vng' && (
                        <VNGSettings config={config} updateConfig={updateConfig} />
                    )}
                    {activeModuleId === 'stimulus_screen' && (
                        <StimulusScreenSettings config={config} updateConfig={updateConfig} />
                    )}
                </div>
            </main>
        </div>
    );
};

export default SettingsView;
