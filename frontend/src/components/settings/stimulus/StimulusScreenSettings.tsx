import React, { useState, useEffect } from 'react';
import { Monitor as MonitorIcon, Ruler, RefreshCw, CheckCircle, AlertTriangle } from 'lucide-react';
import { AppConfig, StimulusDisplayConfig } from '../../../types/config';
import { availableMonitors, Monitor } from '@tauri-apps/api/window';
import { listen, emit, UnlistenFn } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/core';

interface StimulusScreenSettingsProps {
    config: AppConfig;
    updateConfig: (section: keyof AppConfig, data: any) => void;
}

export const StimulusScreenSettings: React.FC<StimulusScreenSettingsProps> = ({ config, updateConfig }) => {
    const [monitors, setMonitors] = useState<Monitor[]>([]);
    const [selectedMonitor, setSelectedMonitor] = useState<Monitor | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    
    // Local state for editing before saving, initialized from config
    const [localConfig, setLocalConfig] = useState<StimulusDisplayConfig>(config.stimulus_screen.display || {
        monitor_name: '',
        monitor_index: -1,
        scale_factor: 1,
        resolution_width: 0,
        resolution_height: 0,
        physical_width_mm: 0,
        physical_height_mm: 0,
        distance_cm: 100,
        is_calibrated: false,
        pixel_density: 0
    });

    useEffect(() => {
        loadMonitors();
    }, []);

    useEffect(() => {
        let unlisten: UnlistenFn;

        const setupListener = async () => {
            unlisten = await listen('calibration_complete', (event: any) => {
                const { ppi } = event.payload;
                console.log("Calibration received:", event.payload);
                
                // Update config
                // We need to access the current localConfig state, but inside the callback it might be stale.
                // Best to update using the functional update form if possible, but here we just need to merge.
                // Or just assume `selectedMonitor` is still valid (it should be).
                
                setLocalConfig(prev => {
                    const newConfig = {
                        ...prev,
                        pixel_density: ppi,
                        is_calibrated: true,
                        // Update physical dimensions based on PPI and resolution if needed? 
                        // No, physical dimensions are usually fixed, PPI is the derived value for rendering.
                        // But if we want to reverse-calc physical width:
                        // width_mm = (resolution_width / ppi) * 25.4
                    };
                    updateConfig('stimulus_screen', { display: newConfig });
                    return newConfig;
                });
            });
        };

        setupListener();

        return () => {
            if (unlisten) unlisten();
        };
    }, []);

    const loadMonitors = async () => {
        setIsLoading(true);
        try {
            const list = await availableMonitors();
            setMonitors(list);
            
            // Try to find the currently configured monitor
            if (config.stimulus_screen.display?.monitor_name) {
                const found = list.find(m => m.name === config.stimulus_screen.display.monitor_name);
                if (found) setSelectedMonitor(found);
            }
        } catch (error) {
            console.error("Failed to load monitors:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleMonitorSelect = (monitor: Monitor, index: number) => {
        setSelectedMonitor(monitor);
        const newConfig = {
            ...localConfig,
            monitor_name: monitor.name || `Monitor ${index + 1}`,
            monitor_index: index,
            scale_factor: monitor.scaleFactor,
            resolution_width: monitor.size.width,
            resolution_height: monitor.size.height,
            // Reset calibration if monitor changes
            is_calibrated: false
        };
        setLocalConfig(newConfig);
        updateConfig('stimulus_screen', { display: newConfig });
    };

    const handleOpenCalibration = async () => {
        try {
            // Open the universal external display window
            await invoke('open_external_display');
            
            // Allow window to load
            await new Promise(r => setTimeout(r, 500));

            // Force it into calibration wizard mode via event (handled by ExternalDisplayPage)
            await emit('start_calibration_wizard');
            
            console.log('Calibration request sent to external display');
        } catch (e) {
            console.error("Failed to open calibration window", e);
        }
    };

    const [diagonalInches, setDiagonalInches] = useState<string>('');

    const calculateFromDiagonal = () => {
        const inches = parseFloat(diagonalInches);
        if (!inches || inches <= 0 || !localConfig.resolution_width || !localConfig.resolution_height) return;

        // Pythagorean theorem: W^2 + H^2 = D^2
        // Aspect Ratio (R) = W / H  => W = R * H
        // (R*H)^2 + H^2 = D^2
        // H^2 * (R^2 + 1) = D^2
        // H = D / sqrt(R^2 + 1)

        const wPx = localConfig.resolution_width;
        const hPx = localConfig.resolution_height;
        const ratio = wPx / hPx;

        const heightInches = inches / Math.sqrt(Math.pow(ratio, 2) + 1);
        const widthInches = ratio * heightInches;

        // Convert to mm (1 inch = 25.4 mm)
        const widthMm = widthInches * 25.4;
        const heightMm = heightInches * 25.4;

        // Calculate PPI
        const ppi = wPx / widthInches;

        const newConfig = {
            ...localConfig,
            physical_width_mm: parseFloat(widthMm.toFixed(2)),
            physical_height_mm: parseFloat(heightMm.toFixed(2)),
            pixel_density: parseFloat(ppi.toFixed(2)),
            is_calibrated: true // Assume calibrated since we have physical dims
        };

        setLocalConfig(newConfig);
        updateConfig('stimulus_screen', { display: newConfig });
    };

    const handleManualChange = (field: keyof StimulusDisplayConfig, value: number) => {
        const newConfig = { ...localConfig, [field]: value };
        
        // Auto-calculate PPI if width is present
        if (field === 'physical_width_mm' && value > 0 && newConfig.resolution_width > 0) {
            // PPI = pixels / inches
            // inches = mm / 25.4
            const widthInches = value / 25.4;
            newConfig.pixel_density = newConfig.resolution_width / widthInches;
        }

        setLocalConfig(newConfig);
        updateConfig('stimulus_screen', { display: newConfig });
    };

    return (
        <div className="h-full flex flex-col p-6 overflow-y-auto">
            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                <MonitorIcon className="w-6 h-6 text-purple-400" />
                Configuración de Pantalla de Estímulos
            </h3>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Monitor Selection */}
                <div className="bg-dark-900/50 p-6 rounded-xl border border-dark-800">
                    <div className="flex justify-between items-center mb-4">
                        <h4 className="text-lg font-semibold text-white">1. Selección de Monitor</h4>
                        <button 
                            onClick={loadMonitors} 
                            disabled={isLoading}
                            className="text-xs flex items-center gap-1 text-siev-400 hover:text-siev-300"
                        >
                            <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
                            Actualizar
                        </button>
                    </div>

                    <div className="space-y-3">
                        {monitors.map((m, idx) => (
                            <button
                                key={m.name || idx}
                                onClick={() => handleMonitorSelect(m, idx)}
                                className={`w-full flex items-center p-4 rounded-lg border transition-all ${
                                    selectedMonitor?.name === m.name
                                        ? 'bg-purple-500/10 border-purple-500/50 text-white'
                                        : 'bg-dark-950 border-dark-800 text-dark-400 hover:border-dark-700'
                                }`}
                            >
                                <div className="p-3 rounded-full bg-dark-900 mr-4">
                                    <MonitorIcon className={`w-6 h-6 ${selectedMonitor?.name === m.name ? 'text-purple-400' : 'text-dark-600'}`} />
                                </div>
                                <div className="text-left">
                                    <div className="font-medium">{m.name || `Monitor ${idx + 1}`}</div>
                                    <div className="text-xs opacity-70">
                                        {m.size.width}x{m.size.height} @ {m.scaleFactor}x
                                    </div>
                                    <div className="text-xs opacity-50 font-mono mt-1">
                                        Pos: ({m.position.x}, {m.position.y})
                                    </div>
                                </div>
                                {selectedMonitor?.name === m.name && (
                                    <CheckCircle className="w-5 h-5 text-purple-400 ml-auto" />
                                )}
                            </button>
                        ))}
                    </div>

                    {!selectedMonitor && (
                        <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg flex gap-3 text-yellow-200 text-sm">
                            <AlertTriangle className="w-5 h-5 shrink-0" />
                            <p>Seleccione el monitor donde se mostrarán los estímulos visuales.</p>
                        </div>
                    )}
                </div>

                {/* Calibration */}
                <div className={`space-y-6 ${!selectedMonitor ? 'opacity-50 pointer-events-none' : ''}`}>
                    
                    {/* Physical Dimensions */}
                    <div className="bg-dark-900/50 p-6 rounded-xl border border-dark-800">
                        <h4 className="text-lg font-semibold text-white mb-4">2. Dimensiones Físicas</h4>
                        
                        {/* Diagonal Calculator */}
                        <div className="mb-6 pb-6 border-b border-dark-800">
                            <label className="block text-xs text-dark-400 mb-2">Opción A: Calcular desde Diagonal (Pulgadas)</label>
                            <div className="flex gap-2">
                                <div className="relative flex-1">
                                    <input 
                                        type="number" 
                                        value={diagonalInches}
                                        onChange={(e) => setDiagonalInches(e.target.value)}
                                        className="w-full bg-dark-950 border border-dark-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-purple-500 placeholder-dark-600"
                                        placeholder="Ej: 24, 27, 32..."
                                    />
                                    <span className="absolute right-3 top-2 text-dark-600 text-xs">inch</span>
                                </div>
                                <button
                                    onClick={calculateFromDiagonal}
                                    disabled={!diagonalInches || parseFloat(diagonalInches) <= 0}
                                    className="bg-dark-800 hover:bg-dark-700 text-white px-4 py-2 rounded-lg text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-dark-700"
                                >
                                    Calcular
                                </button>
                            </div>
                        </div>

                        <div className="mb-2">
                            <label className="block text-xs text-dark-400 mb-2">Opción B: Introducir Manualmente</label>
                        </div>
                        <div className="grid grid-cols-2 gap-4 mb-4">
                            <div>
                                <label className="block text-xs text-dark-400 mb-1">Ancho Pantalla (mm)</label>
                                <div className="relative">
                                    <input 
                                        type="number" 
                                        value={localConfig.physical_width_mm || ''}
                                        onChange={(e) => handleManualChange('physical_width_mm', parseFloat(e.target.value))}
                                        className="w-full bg-dark-950 border border-dark-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-purple-500"
                                        placeholder="0.00"
                                    />
                                    <span className="absolute right-3 top-2 text-dark-600 text-xs">mm</span>
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs text-dark-400 mb-1">Alto Pantalla (mm)</label>
                                <div className="relative">
                                    <input 
                                        type="number" 
                                        value={localConfig.physical_height_mm || ''}
                                        onChange={(e) => handleManualChange('physical_height_mm', parseFloat(e.target.value))}
                                        className="w-full bg-dark-950 border border-dark-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-purple-500"
                                        placeholder="0.00"
                                    />
                                    <span className="absolute right-3 top-2 text-dark-600 text-xs">mm</span>
                                </div>
                            </div>
                        </div>

                        <div>
                            <label className="block text-xs text-dark-400 mb-1">Distancia Paciente (cm)</label>
                            <div className="relative">
                                <input 
                                    type="number" 
                                    value={localConfig.distance_cm || 100}
                                    onChange={(e) => handleManualChange('distance_cm', parseFloat(e.target.value))}
                                    className="w-full bg-dark-950 border border-dark-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-purple-500"
                                />
                                <span className="absolute right-3 top-2 text-dark-600 text-xs">cm</span>
                            </div>
                        </div>
                    </div>

                    {/* Calibration Action */}
                    <div className="bg-dark-900/50 p-6 rounded-xl border border-dark-800">
                         <h4 className="text-lg font-semibold text-white mb-4">3. Calibración</h4>
                         <p className="text-sm text-dark-400 mb-4">
                             Es necesario calibrar la pantalla para asegurar que los estímulos visuales tengan el tamaño angular correcto.
                         </p>

                         <div className="flex items-center justify-between p-4 bg-dark-950 rounded-lg border border-dark-700 mb-4">
                             <div>
                                 <div className="text-sm text-dark-300">Densidad de Píxeles</div>
                                 <div className="text-xl font-mono text-white">
                                     {localConfig.pixel_density > 0 ? localConfig.pixel_density.toFixed(2) : '--'} <span className="text-sm text-dark-500">PPI</span>
                                 </div>
                             </div>
                             {localConfig.is_calibrated ? (
                                 <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded border border-green-500/30">Calibrado</span>
                             ) : (
                                 <span className="px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded border border-red-500/30">No Calibrado</span>
                             )}
                         </div>

                         <button
                            onClick={handleOpenCalibration}
                            className="w-full py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-lg flex items-center justify-center gap-2 transition-colors"
                         >
                             <Ruler className="w-5 h-5" />
                             Abrir Asistente de Calibración
                         </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
