import React, { useState } from 'react';
import { FileText, ClipboardList, BookOpen, BarChart3 } from 'lucide-react';
import { SettingsTabs, TabDefinition } from '../SettingsTabs';
import { ReportTab } from './ReportTab';
import { TestsTab } from './TestsTab';
import { ReferencesTab } from './ReferencesTab';
import { ClassificationTab } from './ClassificationTab';

interface ImpedanciometriaSettingsProps {
    config: any;
    updateConfig: (path: string, value: any) => void;
}

const IMPEDANCIOMETRIA_TABS: TabDefinition[] = [
    { id: 'report', label: 'Informe', icon: FileText },
    { id: 'tests', label: 'Pruebas', icon: ClipboardList },
    { id: 'references', label: 'Curvas de Referencia', icon: BookOpen },
    { id: 'classification', label: 'Clasificación', icon: BarChart3 },
];

export const ImpedanciometriaSettings: React.FC<ImpedanciometriaSettingsProps> = ({ config, updateConfig }) => {
    const [activeTab, setActiveTab] = useState('report');

    return (
        <div className="flex flex-col h-full">
            <SettingsTabs
                tabs={IMPEDANCIOMETRIA_TABS}
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
                {activeTab === 'classification' && (
                    <ClassificationTab config={config} updateConfig={updateConfig} />
                )}
            </div>
        </div>
    );
};
