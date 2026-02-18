import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Settings, Save, RotateCcw, FileText, Activity, Monitor, LayoutGrid, Zap, Crosshair, Ear, Eye, BarChart3, RotateCcw as RotateCcwIcon } from 'lucide-react';
import { useSettingsConfig } from '../hooks/useSettingsConfig';
import { ModuleSelector, ModuleDefinition, TestBattery } from './settings/ModuleSelector';
import { GeneralSettings } from './settings/general';
import { VNGSettings } from './settings/vng';
import { AudiometriaSettings } from './settings/audiometria';
import { OtoscopiaSettings } from './settings/otoscopia';
import { ImpedanciometriaSettings } from './settings/impedanciometria';
import { PosturalSettings } from './settings/postural';
import { useWebSocket } from '../contexts/WebSocketContext';
import { StimulusScreenSettings } from './settings/stimulus/StimulusScreenSettings';
import { TestBatteryEditor } from './settings/TestBatteryEditor';

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
        label: 'VPPB',
        name: 'Postural / VPPB',
        icon: RotateCcwIcon,
        imagePath: '/mod_imu.png',
        color: 'text-orange-400',
        description: 'Diagnóstico y tratamiento de VPPB con seguimiento cefálico 3D.'
    },
    {
        id: 'vemp',
        label: 'VEMP',
        name: 'Potenciales Miogénicos',
        icon: Zap,
        color: 'text-red-400',
        description: 'Respuestas vestibulares evocadas (cervical/ocular).'
    },
    {
        id: 'point_projector',
        label: 'LASER',
        name: 'Proyector de Puntos',
        icon: Crosshair,
        imagePath: '/mod_laser.png',
        color: 'text-yellow-400',
        description: 'Hardware externo para calibración y seguimiento láser.'
    },
    {
        id: 'audiometria',
        label: 'AUDIO',
        name: 'Evaluación Auditiva',
        icon: Ear,
        color: 'text-teal-400',
        description: 'Evaluación auditiva tonal, vocal y supraliminar.',
        isReportOnly: true
    },
    {
        id: 'otoscopia',
        label: 'OTSC',
        name: 'Otoscopia',
        icon: Eye,
        color: 'text-amber-400',
        description: 'Registro de hallazgos otoscópicos.',
        isReportOnly: true
    },
    {
        id: 'impedanciometria',
        label: 'IMPED',
        name: 'Impedanciometría',
        icon: BarChart3,
        color: 'text-rose-400',
        description: 'Timpanometría y clasificación Jerger.',
        isReportOnly: true
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
    const [generalInitialTab, setGeneralInitialTab] = useState<string | undefined>(undefined);
    const [batteries, setBatteries] = useState<TestBattery[]>(() => {
        try {
            const stored = localStorage.getItem('siev_test_batteries');
            return stored ? JSON.parse(stored) : [];
        } catch { return []; }
    });
    const [editingBattery, setEditingBattery] = useState<TestBattery | null>(null);
    const [selectedBatteryId, setSelectedBatteryId] = useState<string | null>(null);

    useEffect(() => {
        localStorage.setItem('siev_test_batteries', JSON.stringify(batteries));
    }, [batteries]);

    // Auto-save on exit logic
    const configRef = useRef(config);
    const isDirtyRef = useRef(isDirty);

    useEffect(() => {
        configRef.current = config;
        isDirtyRef.current = isDirty;
    }, [config, isDirty]);

    useEffect(() => {
        return () => {
            // When leaving the component, if there are unsaved changes, save them
            if (isDirtyRef.current && configRef.current) {
                console.log('[SettingsView] Auto-saving changes on exit...');
                saveConfig();
            }
        };
    }, [saveConfig]);

    const handleModuleSelect = useCallback((id: string) => {
        setActiveModuleId(id);
        setGeneralInitialTab(undefined);
        setSelectedBatteryId(null);
    }, []);

    const handleNavigateToModules = useCallback(() => {
        setActiveModuleId('general');
        setGeneralInitialTab('modules');
        setSelectedBatteryId(null);
    }, []);

    const handleCreateBattery = useCallback(() => {
        setActiveModuleId('test_battery_editor');
        setEditingBattery(null);
        setSelectedBatteryId(null);
    }, []);

    const handleSelectBattery = useCallback((id: string) => {
        setSelectedBatteryId(id);
        const battery = batteries.find(b => b.id === id);
        if (battery) {
            setEditingBattery(battery);
            setActiveModuleId('test_battery_editor');
        }
    }, [batteries]);

    const handleSaveBattery = useCallback((battery: TestBattery) => {
        setBatteries(prev => {
            const existing = prev.findIndex(b => b.id === battery.id);
            if (existing >= 0) {
                const next = [...prev];
                next[existing] = battery;
                return next;
            }
            return [...prev, battery];
        });
        setActiveModuleId('general');
        setEditingBattery(null);
        setSelectedBatteryId(null);
    }, []);

    const handleCancelBattery = useCallback(() => {
        setActiveModuleId('general');
        setEditingBattery(null);
        setSelectedBatteryId(null);
    }, []);

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
                <div className="flex justify-between items-center">
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
            </header>

            {/* Body: Sidebar + Content */}
            <div className="flex-1 flex overflow-hidden">
                <ModuleSelector
                    modules={MODULE_LIST}
                    activeModuleId={activeModuleId}
                    onModuleSelect={handleModuleSelect}
                    activeStates={config.modules}
                    batteries={batteries}
                    onNavigateToModules={handleNavigateToModules}
                    onCreateBattery={handleCreateBattery}
                    onSelectBattery={handleSelectBattery}
                    selectedBatteryId={selectedBatteryId}
                />

                <main className="flex-1 overflow-hidden px-6 py-2">
                    <div className="max-w-5xl mx-auto h-full flex flex-col">
                        {activeModuleId === 'general' && (
                            <GeneralSettings config={config} updateConfig={updateConfig} initialTab={generalInitialTab} />
                        )}
                        {activeModuleId === 'vng' && (
                            <VNGSettings config={config} updateConfig={updateConfig} />
                        )}
                        {activeModuleId === 'stimulus_screen' && (
                            <StimulusScreenSettings config={config} updateConfig={updateConfig} />
                        )}
                        {activeModuleId === 'audiometria' && (
                            <AudiometriaSettings config={config} updateConfig={updateConfig} />
                        )}
                        {activeModuleId === 'otoscopia' && (
                            <OtoscopiaSettings config={config} updateConfig={updateConfig} />
                        )}
                        {activeModuleId === 'impedanciometria' && (
                            <ImpedanciometriaSettings config={config} updateConfig={updateConfig} />
                        )}
                        {activeModuleId === 'imu_posturography' && (
                            <PosturalSettings config={config} updateConfig={updateConfig} />
                        )}
                        {activeModuleId === 'test_battery_editor' && (
                            <TestBatteryEditor
                                onSave={handleSaveBattery}
                                onCancel={handleCancelBattery}
                                editingBattery={editingBattery}
                            />
                        )}
                    </div>
                </main>
            </div>
        </div>
    );
};

export default SettingsView;
