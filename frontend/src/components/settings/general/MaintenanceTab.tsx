import React, { useState } from 'react';
import { Trash2, AlertTriangle, RefreshCw } from 'lucide-react';
import { invoke } from '@tauri-apps/api/core';

export const MaintenanceTab: React.FC = () => {
    const [isConfirming, setIsConfirming] = useState(false);
    const [isResetting, setIsResetting] = useState(false);

    const handleReset = async () => {
        setIsResetting(true);
        try {
            await invoke('reset_application');
            // Reload the application to start from scratch
            window.location.reload();
        } catch (error) {
            console.error('Failed to reset application:', error);
            setIsResetting(false);
            setIsConfirming(false);
            alert('Error al reiniciar la aplicación: ' + error);
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-6">
                <div className="flex items-start gap-4">
                    <div className="p-3 bg-red-500/10 rounded-lg">
                        <Trash2 className="w-6 h-6 text-red-500" />
                    </div>
                    <div className="flex-1">
                        <h3 className="text-lg font-bold text-white mb-1">Reiniciar Aplicación</h3>
                        <p className="text-sm text-dark-400 mb-6">
                            Esta acción eliminará todos los datos de la base de datos (pacientes, sesiones, especialistas y configuraciones).
                            <span className="block mt-2 font-bold text-red-400">
                                Los archivos de video y datos guardados en el disco duro NO serán eliminados, pero la aplicación olvidará su ubicación y volverá al estado inicial de fábrica.
                            </span>
                        </p>

                        {!isConfirming ? (
                            <button
                                onClick={() => setIsConfirming(true)}
                                className="bg-red-600 hover:bg-red-500 text-white px-4 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2"
                            >
                                <AlertTriangle className="w-4 h-4" />
                                Eliminar todo y reiniciar
                            </button>
                        ) : (
                            <div className="bg-dark-900/80 p-4 rounded-lg border border-red-500/30">
                                <p className="text-sm font-bold text-red-400 mb-4 flex items-center gap-2">
                                    <AlertTriangle className="w-4 h-4" />
                                    ¿Estás absolutamente seguro? Esta acción es irreversible.
                                </p>
                                <div className="flex gap-3">
                                    <button
                                        disabled={isResetting}
                                        onClick={handleReset}
                                        className="bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2"
                                    >
                                        {isResetting ? (
                                            <RefreshCw className="w-4 h-4 animate-spin" />
                                        ) : (
                                            <Trash2 className="w-4 h-4" />
                                        )}
                                        {isResetting ? 'Reiniciando...' : 'Sí, borrar todo'}
                                    </button>
                                    <button
                                        disabled={isResetting}
                                        onClick={() => setIsConfirming(false)}
                                        className="bg-dark-700 hover:bg-dark-600 text-white px-4 py-2 rounded-lg text-sm font-bold transition-all"
                                    >
                                        Cancelar
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <div className="bg-dark-900/50 border border-dark-800 rounded-xl p-6">
                <h4 className="text-sm font-bold text-dark-300 mb-2">Información del Sistema</h4>
                <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-dark-800/50 rounded-lg border border-dark-700">
                        <p className="text-[10px] text-dark-500 uppercase font-bold mb-1">Versión de App</p>
                        <p className="text-sm text-white font-mono">1.0.0</p>
                    </div>
                    <div className="p-3 bg-dark-800/50 rounded-lg border border-dark-700">
                        <p className="text-[10px] text-dark-500 uppercase font-bold mb-1">Entorno</p>
                        <p className="text-sm text-white">Producción (Linux)</p>
                    </div>
                </div>
            </div>
        </div>
    );
};
