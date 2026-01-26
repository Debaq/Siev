import React from 'react';
import { Database, FolderOpen, HardDrive, ShieldCheck, AlertCircle } from 'lucide-react';
import { open } from '@tauri-apps/plugin-dialog';

interface StorageTabProps {
    config: any;
    updateConfig: (path: string, value: any) => void;
}

export const StorageTab: React.FC<StorageTabProps> = ({ config, updateConfig }) => {
    const handleSelectPath = async () => {
        try {
            const selected = await open({
                directory: true,
                multiple: false,
                title: 'Seleccionar Carpeta de Almacenamiento'
            });

            if (selected) {
                updateConfig('general.storage.data_path', selected);
            }
        } catch (error) {
            console.error('Error selecting directory:', error);
        }
    };

    const storagePath = config.general?.storage?.data_path || 'No configurado';

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {/* Header Section */}
            <div className="bg-dark-900/50 rounded-2xl p-6 border border-dark-800">
                <div className="flex items-start gap-4">
                    <div className="p-3 bg-siev-500/10 rounded-xl border border-siev-500/20">
                        <Database className="w-6 h-6 text-siev-400" />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-white mb-1">Ruta de Almacenamiento</h3>
                        <p className="text-sm text-dark-400 max-w-2xl">
                            Defina dónde se guardarán todos los archivos del sistema (.siev), incluyendo videos, 
                            telemetría de pacientes e informes generados.
                        </p>
                    </div>
                </div>

                <div className="mt-6 flex flex-col gap-3">
                    <label className="text-xs font-bold text-dark-500 uppercase tracking-widest px-1">
                        Directorio de Trabajo Actual
                    </label>
                    <div className="flex gap-2">
                        <div className="flex-1 bg-dark-950 border border-dark-700 rounded-xl px-4 py-3 flex items-center gap-3 group focus-within:border-siev-500/50 transition-all">
                            <HardDrive className="w-4 h-4 text-dark-500 group-hover:text-siev-400 transition-colors" />
                            <span className="text-sm text-dark-200 font-mono truncate">{storagePath}</span>
                        </div>
                        <button 
                            onClick={handleSelectPath}
                            className="bg-dark-800 hover:bg-dark-700 text-white px-4 py-3 rounded-xl border border-dark-700 transition-all flex items-center gap-2 font-medium"
                        >
                            <FolderOpen className="w-4 h-4 text-siev-400" />
                            Cambiar
                        </button>
                    </div>
                </div>
            </div>

            {/* Information Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-dark-900/30 rounded-2xl p-5 border border-dark-800 flex gap-4">
                    <div className="p-2 bg-blue-500/10 rounded-lg h-fit">
                        <ShieldCheck className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                        <h4 className="text-sm font-bold text-white mb-1">Portabilidad Total</h4>
                        <p className="text-xs text-dark-500 leading-relaxed">
                            Al usar carpetas .siev, puede mover sus datos a cualquier otro equipo con SIEV 
                            simplemente copiando esta carpeta.
                        </p>
                    </div>
                </div>

                <div className="bg-dark-900/30 rounded-2xl p-5 border border-dark-800 flex gap-4">
                    <div className="p-2 bg-yellow-500/10 rounded-lg h-fit">
                        <AlertCircle className="w-5 h-5 text-yellow-400" />
                    </div>
                    <div>
                        <h4 className="text-sm font-bold text-white mb-1">Discos Externos</h4>
                        <p className="text-xs text-dark-500 leading-relaxed">
                            Se recomienda usar discos de estado sólido (SSD) para garantizar una grabación 
                            de video fluida y sin saltos de frames.
                        </p>
                    </div>
                </div>
            </div>

            {/* Settings */}
            <div className="bg-dark-900/50 rounded-2xl p-6 border border-dark-800">
                <h3 className="text-sm font-bold text-white mb-4 uppercase tracking-wider">Opciones Adicionales</h3>
                
                <div className="space-y-4">
                    <label className="flex items-center justify-between p-3 rounded-xl hover:bg-dark-800/50 transition-colors cursor-pointer group">
                        <div className="flex flex-col gap-0.5">
                            <span className="text-sm font-medium text-dark-200 group-hover:text-white transition-colors">Copia de Seguridad Automática</span>
                            <span className="text-xs text-dark-500">Sincronizar datos con un servidor secundario o nube configurada.</span>
                        </div>
                        <div className="relative inline-flex items-center cursor-pointer">
                            <input 
                                type="checkbox" 
                                className="sr-only peer"
                                checked={config.general?.storage?.backup_enabled || false}
                                onChange={(e) => updateConfig('general.storage.backup_enabled', e.target.checked)}
                            />
                            <div className="w-10 h-5 bg-dark-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-siev-600"></div>
                        </div>
                    </label>
                </div>
            </div>
        </div>
    );
};
