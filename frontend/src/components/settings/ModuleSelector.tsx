import React from 'react';
import { LucideIcon, FileText, Activity, Monitor, LayoutGrid, Lock } from 'lucide-react';

export interface ModuleDefinition {
    id: string;
    label: string;
    name: string;
    icon: LucideIcon;
    color: string;
    description: string;
    isAlwaysVisible?: boolean;
    isLocked?: boolean;
    isSoon?: boolean;
}

interface ModuleSelectorProps {
    modules: ModuleDefinition[];
    activeModuleId: string;
    onModuleSelect: (id: string) => void;
    activeStates: Record<string, boolean>;
}

export const ModuleSelector: React.FC<ModuleSelectorProps> = ({ 
    modules, 
    activeModuleId, 
    onModuleSelect,
    activeStates
}) => {
    return (
        <div className="flex gap-3 overflow-x-auto pb-4 custom-scrollbar">
            {modules.map(mod => {
                const isActive = activeStates[mod.id] || mod.isAlwaysVisible;
                const isSelected = activeModuleId === mod.id;

                if (!isActive) return null;

                return (
                    <button
                        key={mod.id}
                        onClick={() => onModuleSelect(mod.id)}
                        className={`
                            relative min-w-[180px] p-4 rounded-xl border transition-all text-left group
                            ${isSelected 
                                ? `bg-dark-800 ${mod.color.replace('text-', 'border-')}/50 shadow-lg shadow-black/20` 
                                : 'bg-dark-900 border-dark-800 hover:border-dark-700'}
                            cursor-pointer
                        `}
                    >
                        <div className="flex justify-between items-start mb-2">
                            <div className={`p-2 rounded-lg ${isSelected ? 'bg-dark-900' : 'bg-dark-850 group-hover:bg-dark-800'} transition-colors`}>
                                <mod.icon className={`w-5 h-5 ${mod.color}`} />
                            </div>
                        </div>
                        
                        <h4 className={`font-bold text-sm ${isSelected ? 'text-white' : 'text-dark-300 group-hover:text-white'}`}>
                            {mod.name}
                        </h4>
                        <p className="text-[10px] text-dark-500 leading-tight mt-1 line-clamp-2">
                            {mod.description}
                        </p>

                        {isSelected && (
                            <div className={`absolute bottom-0 left-0 right-0 h-1 rounded-b-xl ${mod.color.replace('text-', 'bg-')}`} />
                        )}
                    </button>
                );
            })}
        </div>
    );
};
