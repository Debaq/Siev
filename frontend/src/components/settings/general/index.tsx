import React, { useState } from 'react';
import { FileText, Users, LayoutGrid, Database } from 'lucide-react';
import { SettingsTabs, TabDefinition } from '../SettingsTabs';
import { InstitutionTab } from './InstitutionTab';
import { TeamTab } from './TeamTab';
import { ModulesTab } from './ModulesTab';
import { StorageTab } from './StorageTab';

interface GeneralSettingsProps {
    config: any;
    updateConfig: (path: string, value: any) => void;
}

const GENERAL_TABS: TabDefinition[] = [
    { id: 'institution', label: 'Institución', icon: FileText },
    { id: 'team', label: 'Equipo', icon: Users },
    { id: 'modules', label: 'Módulos', icon: LayoutGrid },
    { id: 'storage', label: 'Almacenamiento', icon: Database },
];

export const GeneralSettings: React.FC<GeneralSettingsProps> = ({ config, updateConfig }) => {
    const [activeTab, setActiveTab] = useState('institution');

    return (
        <div className="flex flex-col h-full">
            <SettingsTabs 
                tabs={GENERAL_TABS} 
                activeTabId={activeTab} 
                onTabChange={setActiveTab} 
            />
            
            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {activeTab === 'institution' && (
                    <InstitutionTab config={config} updateConfig={updateConfig} />
                )}
                {activeTab === 'team' && (
                    <TeamTab />
                )}
                {activeTab === 'modules' && (
                    <ModulesTab config={config} updateConfig={updateConfig} />
                )}
                {activeTab === 'storage' && (
                    <StorageTab config={config} updateConfig={updateConfig} />
                )}
            </div>
        </div>
    );
};
