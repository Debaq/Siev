import React, { useState } from 'react'
import { ClipboardList, Timer, Box, Heart } from 'lucide-react'
import { SettingsTabs, TabDefinition } from '../SettingsTabs'
import { TestsTab } from './TestsTab'
import { TimingTab } from './TimingTab'
import { VisualizationTab } from './VisualizationTab'
import { SymptomsTab } from './SymptomsTab'

interface PosturalSettingsProps {
    config: any
    updateConfig: (path: string, value: any) => void
}

const POSTURAL_TABS: TabDefinition[] = [
    { id: 'tests', label: 'Pruebas', icon: ClipboardList },
    { id: 'timing', label: 'Tiempos', icon: Timer },
    { id: 'visualization', label: 'Visualización', icon: Box },
    { id: 'symptoms', label: 'Síntomas', icon: Heart },
]

export const PosturalSettings: React.FC<PosturalSettingsProps> = ({ config, updateConfig }) => {
    const [activeTab, setActiveTab] = useState('tests')

    return (
        <div className="flex flex-col h-full">
            <SettingsTabs
                tabs={POSTURAL_TABS}
                activeTabId={activeTab}
                onTabChange={setActiveTab}
            />

            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {activeTab === 'tests' && (
                    <TestsTab config={config} updateConfig={updateConfig} />
                )}
                {activeTab === 'timing' && (
                    <TimingTab config={config} updateConfig={updateConfig} />
                )}
                {activeTab === 'visualization' && (
                    <VisualizationTab config={config} updateConfig={updateConfig} />
                )}
                {activeTab === 'symptoms' && (
                    <SymptomsTab config={config} updateConfig={updateConfig} />
                )}
            </div>
        </div>
    )
}
