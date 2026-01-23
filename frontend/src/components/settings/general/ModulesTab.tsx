import React from 'react';
import { CheckCircle2 } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsToggle } from '../shared/SettingsToggle';

interface ModulesTabProps {
    config: any;
    updateConfig: (path: string, value: any) => void;
}

const MODULE_DEFINITIONS = [
    { id: 'vng', label: 'VNG', name: 'Video-Oculografía', desc: 'Análisis de nistagmo y movimientos oculares por video de alta velocidad.', color: 'text-cyan-400', border: 'border-cyan-500/30', bg: 'bg-cyan-500/5', icon: '/mod_vng.png' },
    { id: 'stimulus_screen', label: 'VISUAL', name: 'Pantalla de Estímulos', desc: 'Control de optotipos y estímulos optocinéticos en monitor secundario.', color: 'text-purple-400', border: 'border-purple-500/30', bg: 'bg-purple-500/5', icon: '/mod_stimulus.png' },
    { id: 'vhit', label: 'vHIT', name: 'Video Head Impulse', desc: 'Prueba de impulso cefálico asistida por video.', color: 'text-orange-400', border: 'border-orange-500/20', bg: 'bg-dark-800', icon: '/mod_vhit.png' },
    { id: 'static_posturography', label: 'PLAT', name: 'Posturografía Estática', desc: 'Análisis de equilibrio en plataforma de fuerza SIEV.', color: 'text-green-400', border: 'border-green-500/20', bg: 'bg-dark-800', icon: '/mod_posturography.png' },
    { id: 'imu_posturography', label: 'IMU', name: 'Posturografía Inercial', desc: 'Evaluación de balance mediante sensores corporales.', color: 'text-emerald-400', border: 'border-emerald-500/20', bg: 'bg-dark-800', icon: '/mod_imu.png' },
    { id: 'vemp', label: 'VEMP', name: 'Potenciales Miogénicos', desc: 'Respuestas vestibulares evocadas (cervical/ocular).', color: 'text-red-400', border: 'border-red-500/20', bg: 'bg-dark-800' },
    { id: 'point_projector', label: 'LASER', name: 'Proyector de Puntos', desc: 'Hardware externo para calibración y seguimiento láser.', color: 'text-yellow-400', border: 'border-yellow-500/20', bg: 'bg-dark-800', icon: '/mod_laser.png' },
];

export const ModulesTab: React.FC<ModulesTabProps> = ({ config, updateConfig }) => {
    return (
        <div className="space-y-6 animate-fade-in">
            <SettingsSection 
                title="Módulos del Sistema" 
                description="Active o desactive los componentes del ecosistema SIEV disponibles en su licencia."
            >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {MODULE_DEFINITIONS.map(mod => {
                        const isEnabled = config.modules[mod.id];
                        return (
                            <div 
                                key={mod.id} 
                                className={`relative p-4 rounded-xl border transition-all flex gap-4 ${isEnabled ? mod.border + ' ' + mod.bg : 'border-dark-800 bg-dark-900 opacity-60'}`}
                            >
                                <div className={`w-16 h-16 rounded-lg bg-dark-950 flex items-center justify-center flex-shrink-0 border border-dark-800 overflow-hidden`}>
                                    {mod.icon ? (
                                        <img src={mod.icon} alt={mod.label} className="w-12 h-12 object-contain" />
                                    ) : (
                                        <div className={`text-xl font-bold ${mod.color}`}>{mod.label[0]}</div>
                                    )}
                                </div>

                                <div className="flex-1 min-w-0">
                                    <div className="flex justify-between items-start mb-1">
                                        <div className="flex items-center gap-2">
                                            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded bg-dark-950 border border-dark-700 ${mod.color}`}>
                                                {mod.label}
                                            </span>
                                        </div>
                                        
                                        <SettingsToggle 
                                            checked={isEnabled}
                                            onChange={val => updateConfig(`modules.${mod.id}`, val)}
                                        />
                                    </div>
                                    
                                    <h4 className={`font-bold text-xs mb-0.5 ${isEnabled ? 'text-white' : 'text-dark-400'}`}>
                                        {mod.name}
                                    </h4>
                                    <p className="text-[10px] text-dark-500 leading-tight">
                                        {mod.desc}
                                    </p>
                                </div>
                                
                                {isEnabled && (
                                    <div className="absolute top-1 right-1">
                                        <div className={`p-0.5 rounded-full bg-dark-950`}>
                                            <CheckCircle2 className={`w-3 h-3 ${mod.color}`} />
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </SettingsSection>
        </div>
    );
};
