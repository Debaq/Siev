import React, { useState } from 'react';
import { Camera, Cpu, Monitor, Activity, FileText } from 'lucide-react';
import { SettingsTabs, TabDefinition } from '../SettingsTabs';
import { CameraTab } from './CameraTab';
import { AlgorithmTab } from './AlgorithmTab';
import { HardwareTab } from './HardwareTab';
import { CalibrationTab } from './CalibrationTab';

interface VNGSettingsProps {
    config: any;
    updateConfig: (path: string, value: any) => void;
}

const VNG_TABS: TabDefinition[] = [
    { id: 'camera', label: 'Cámara', icon: Camera },
    { id: 'algorithm', label: 'Algoritmo', icon: Cpu },
    { id: 'hardware', label: 'Hardware', icon: Monitor },
    { id: 'calibration', label: 'Calibración', icon: Activity },
    { id: 'report', label: 'Informe', icon: FileText },
];

export const VNGSettings: React.FC<VNGSettingsProps> = ({ config, updateConfig }) => {
    const [activeTab, setActiveTab] = useState('camera');

    return (
        <div className="flex flex-col h-full">
            <SettingsTabs 
                tabs={VNG_TABS} 
                activeTabId={activeTab} 
                onTabChange={setActiveTab} 
            />
            
            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {activeTab === 'camera' && (
                    <CameraTab config={config} updateConfig={updateConfig} />
                )}
                {activeTab === 'algorithm' && (
                    <AlgorithmTab config={config} updateConfig={updateConfig} />
                )}
                {activeTab === 'hardware' && (
                    <HardwareTab config={config} updateConfig={updateConfig} />
                )}
                {activeTab === 'calibration' && (
                    <CalibrationTab config={config} updateConfig={updateConfig} />
                )}
                {activeTab === 'report' && (
                    <div className="p-10 text-center text-dark-500 italic">
                        Configuración de reportes próximamente...
                    </div>
                )}
            </div>
        </div>
    );
};
