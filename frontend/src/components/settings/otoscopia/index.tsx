import React, { useState } from 'react';
import { FileText, Search, MapPin, ImageIcon } from 'lucide-react';
import { SettingsTabs, TabDefinition } from '../SettingsTabs';
import { ReportTab } from './ReportTab';
import { FindingsTab } from './FindingsTab';
import { RegionsTab } from './RegionsTab';
import { ImagesTab } from './ImagesTab';

interface OtoscopiaSettingsProps {
    config: any;
    updateConfig: (path: string, value: any) => void;
}

const OTOSCOPIA_TABS: TabDefinition[] = [
    { id: 'report', label: 'Informe', icon: FileText },
    { id: 'findings', label: 'Hallazgos', icon: Search },
    { id: 'regions', label: 'Regiones', icon: MapPin },
    { id: 'images', label: 'Imágenes', icon: ImageIcon },
];

export const OtoscopiaSettings: React.FC<OtoscopiaSettingsProps> = ({ config, updateConfig }) => {
    const [activeTab, setActiveTab] = useState('report');

    return (
        <div className="flex flex-col h-full">
            <SettingsTabs
                tabs={OTOSCOPIA_TABS}
                activeTabId={activeTab}
                onTabChange={setActiveTab}
            />

            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {activeTab === 'report' && (
                    <ReportTab config={config} updateConfig={updateConfig} />
                )}
                {activeTab === 'findings' && (
                    <FindingsTab config={config} updateConfig={updateConfig} />
                )}
                {activeTab === 'regions' && (
                    <RegionsTab config={config} updateConfig={updateConfig} />
                )}
                {activeTab === 'images' && (
                    <ImagesTab config={config} updateConfig={updateConfig} />
                )}
            </div>
        </div>
    );
};
