import React, { useState, useEffect } from 'react';
import { FileText, Users, LayoutGrid, Database, ShieldAlert } from 'lucide-react';
import { SettingsTabs, TabDefinition } from '../SettingsTabs';
import { InstitutionTab } from './InstitutionTab';
import { TeamTab } from './TeamTab';
import { ModulesTab } from './ModulesTab';
import { StorageTab } from './StorageTab';
import { MaintenanceTab } from './MaintenanceTab';

interface GeneralSettingsProps {
    config: any;
    updateConfig: (path: string, value: any) => void;
    initialTab?: string;
}

const GENERAL_TABS: TabDefinition[] = [
    { id: 'institution', label: 'Institución', icon: FileText },
    { id: 'team', label: 'Equipo', icon: Users },
    { id: 'modules', label: 'Módulos', icon: LayoutGrid },
    { id: 'storage', label: 'Almacenamiento', icon: Database },
    { id: 'maintenance', label: 'Mantenimiento', icon: ShieldAlert },
];

export const GeneralSettings: React.FC<GeneralSettingsProps> = ({ config, updateConfig, initialTab }) => {
    const [activeTab, setActiveTab] = useState(initialTab ?? 'institution');

    useEffect(() => {
        if (initialTab) setActiveTab(initialTab);
    }, [initialTab]);

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
                {activeTab === 'maintenance' && (
                    <MaintenanceTab />
                )}
            </div>
        </div>
    );
};
