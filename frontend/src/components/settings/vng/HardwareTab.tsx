import React from 'react';
import { Monitor, RefreshCw } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsField } from '../shared/SettingsField';
import { useTauriHardware } from '../../../hooks/useTauriHardware';

interface HardwareTabProps {
    config: any;
    updateConfig: (path: string, value: any) => void;
}

export const HardwareTab: React.FC<HardwareTabProps> = ({ config, updateConfig }) => {
    const { ports, connect, disconnect, isConnected, refreshPorts } = useTauriHardware();

    return (
        <div className="space-y-8 animate-fade-in">
            <SettingsSection 
                title="Hardware de Máscara" 
                description="Conexión con la máscara VNG para control de LEDs IR y sensores."
            >
                <SettingsField label="Puerto Serial">
                    <div className="flex gap-2">
                        <select 
                            className="select flex-1" 
                            value={config.vng.hardware.serial_port}
                            onChange={e => updateConfig('vng.hardware.serial_port', e.target.value)}
                        >
                            <option value="">Seleccione un puerto...</option>
                            {ports.map(p => <option key={p} value={p}>{p}</option>)}
                        </select>
                        <button className="btn btn-secondary p-2 h-auto" onClick={refreshPorts}>
                            <RefreshCw className="w-4 h-4" />
                        </button>
                    </div>
                </SettingsField>

                <div className="flex items-center gap-4 p-4 bg-dark-800/50 rounded-lg border border-dark-700">
                    <div className="flex-1">
                        <div className={`text-sm font-bold ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
                            {isConnected ? 'SISTEMA CONECTADO' : 'SISTEMA DESCONECTADO'}
                        </div>
                        <p className="text-xs text-dark-500">Máscara SIEV v1.0 detectada en {config.vng.hardware.serial_port || 'N/A'}</p>
                    </div>
                    {!isConnected ? (
                        <button 
                            className="btn btn-primary px-6"
                            onClick={() => connect(config.vng.hardware.serial_port, config.vng.hardware.baudrate)}
                            disabled={!config.vng.hardware.serial_port}
                        >
                            Conectar
                        </button>
                    ) : (
                        <button className="btn btn-danger px-6" onClick={disconnect}>
                            Desconectar
                        </button>
                    )}
                </div>

                <SettingsField label="Intensidad LEDs Infrarrojos">
                    <div className="flex items-center gap-4">
                        <input 
                            type="range" min="0" max="4" step="1"
                            className="flex-1 accent-siev-500"
                            value={config.vng.hardware.ir_led_intensity}
                            onChange={e => updateConfig('vng.hardware.ir_led_intensity', Number(e.target.value))}
                        />
                        <span className="text-sm font-mono w-12 text-right">
                            {config.vng.hardware.ir_led_intensity * 25}%
                        </span>
                    </div>
                    <p className="text-xs text-dark-500 mt-1">Ajuste la potencia de los LEDs IR para evitar reflejos o saturación.</p>
                </SettingsField>
            </SettingsSection>
        </div>
    );
};
