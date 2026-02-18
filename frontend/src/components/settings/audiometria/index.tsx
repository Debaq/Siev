import React, { useState } from 'react';
import { FileText, ClipboardList, BookOpen, Music } from 'lucide-react';
import { SettingsTabs, TabDefinition } from '../SettingsTabs';
import { ReportTab } from './ReportTab';
import { TestsTab } from './TestsTab';
import { ReferencesTab } from './ReferencesTab';
import { FrequenciesTab } from './FrequenciesTab';

interface AudiometriaSettingsProps {
    config: any;
    updateConfig: (path: string, value: any) => void;
}

const AUDIOMETRIA_TABS: TabDefinition[] = [
    { id: 'report', label: 'Informe', icon: FileText },
    { id: 'tests', label: 'Pruebas', icon: ClipboardList },
    { id: 'references', label: 'Valores de Referencia', icon: BookOpen },
    { id: 'frequencies', label: 'Frecuencias', icon: Music },
];

export const AudiometriaSettings: React.FC<AudiometriaSettingsProps> = ({ config, updateConfig }) => {
    const [activeTab, setActiveTab] = useState('report');

    return (
        <div className="flex flex-col h-full">
            <SettingsTabs
                tabs={AUDIOMETRIA_TABS}
                activeTabId={activeTab}
                onTabChange={setActiveTab}
            />

            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {activeTab === 'report' && (
                    <ReportTab config={config} updateConfig={updateConfig} />
                )}
                {activeTab === 'tests' && (
                    <TestsTab config={config} updateConfig={updateConfig} />
                )}
                {activeTab === 'references' && (
                    <ReferencesTab config={config} updateConfig={updateConfig} />
                )}
                {activeTab === 'frequencies' && (
                    <FrequenciesTab config={config} updateConfig={updateConfig} />
                )}
            </div>
        </div>
    );
};
