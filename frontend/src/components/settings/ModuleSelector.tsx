import React from 'react';
import { LucideIcon, FileText, Activity, Monitor, LayoutGrid, Lock } from 'lucide-react';

export interface ModuleDefinition {
    id: string;
    label: string;
    name: string;
    icon: LucideIcon;
    imagePath?: string;
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
        <div className="flex gap-2 overflow-x-auto pb-1 custom-scrollbar">
            {modules.map(mod => {
                const isActive = activeStates[mod.id] || mod.isAlwaysVisible;
                const isSelected = activeModuleId === mod.id;

                if (!isActive) return null;

                return (
                    <button
                        key={mod.id}
                        onClick={() => onModuleSelect(mod.id)}
                        className={`
                            relative min-w-[170px] p-2.5 rounded-xl border transition-all text-left group
                            ${isSelected 
                                ? `bg-dark-800 ${mod.color.replace('text-', 'border-')}/50 shadow-lg shadow-black/20` 
                                : 'bg-dark-900 border-dark-800 hover:border-dark-700'}
                            cursor-pointer
                        `}
                    >
                        <div className="flex items-center gap-2 mb-1">
                            <div className={`p-1 rounded-lg ${isSelected ? 'bg-dark-950' : 'bg-dark-850 group-hover:bg-dark-800'} transition-colors shrink-0 w-8 h-8 flex items-center justify-center border border-dark-800`}>
                                {mod.imagePath ? (
                                    <img src={mod.imagePath} alt={mod.name} className="w-6 h-6 object-contain" />
                                ) : (
                                    <mod.icon className={`w-4 h-4 ${mod.color}`} />
                                )}
                            </div>
                            <h4 className={`font-bold text-sm leading-tight ${isSelected ? 'text-white' : 'text-dark-300 group-hover:text-white'}`}>
                                {mod.name}
                            </h4>
                        </div>
                        
                        <p className="text-[10px] text-dark-500 leading-tight line-clamp-2">
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
