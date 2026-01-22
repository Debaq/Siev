import React from 'react';
import { LucideIcon } from 'lucide-react';

export interface TabDefinition {
    id: string;
    label: string;
    icon?: LucideIcon;
}

interface SettingsTabsProps {
    tabs: TabDefinition[];
    activeTabId: string;
    onTabChange: (id: string) => void;
}

export const SettingsTabs: React.FC<SettingsTabsProps> = ({ tabs, activeTabId, onTabChange }) => {
    return (
        <div className="flex items-center gap-1 border-b border-dark-800 mb-6">
            {tabs.map(tab => (
                <button
                    key={tab.id}
                    onClick={() => onTabChange(tab.id)}
                    className={`
                        flex items-center gap-2 px-4 py-3 text-sm font-medium transition-all relative
                        ${activeTabId === tab.id 
                            ? 'text-siev-400' 
                            : 'text-dark-400 hover:text-dark-200 hover:bg-dark-800/50'}
                    `}
                >
                    {tab.icon && <tab.icon className="w-4 h-4" />}
                    {tab.label}
                    {activeTabId === tab.id && (
                        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-siev-500" />
                    )}
                </button>
            ))}
        </div>
    );
};
