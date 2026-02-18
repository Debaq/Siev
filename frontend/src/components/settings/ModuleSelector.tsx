import React from 'react';
import { LucideIcon, Plus } from 'lucide-react';

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
    isReportOnly?: boolean;
}

export interface TestBattery {
    id: string;
    name: string;
    shortName: string;
    description: string;
    testIds: string[];
}

interface ModuleSelectorProps {
    modules: ModuleDefinition[];
    activeModuleId: string;
    onModuleSelect: (id: string) => void;
    activeStates: Record<string, boolean>;
    batteries: TestBattery[];
    onNavigateToModules: () => void;
    onCreateBattery: () => void;
    onSelectBattery?: (id: string) => void;
    selectedBatteryId?: string | null;
}

export const ModuleSelector: React.FC<ModuleSelectorProps> = ({
    modules,
    activeModuleId,
    onModuleSelect,
    activeStates,
    batteries,
    onNavigateToModules,
    onCreateBattery,
    onSelectBattery,
    selectedBatteryId
}) => {
    const generalModule = modules.find(m => m.id === 'general');
    const otherModules = modules.filter(m => m.id !== 'general');
    const isGeneralSelected = activeModuleId === 'general' && !selectedBatteryId;

    return (
        <div className="w-48 border-r border-dark-800 flex flex-col shrink-0 overflow-y-auto custom-scrollbar">
            {/* General — fuera de módulos */}
            {generalModule && (
                <div className="flex flex-col">
                    <button
                        onClick={() => onModuleSelect('general')}
                        className={`
                            w-full flex items-center gap-2.5 px-3 py-2.5 text-sm font-medium transition-all text-left
                            border-r-2
                            ${isGeneralSelected
                                ? `text-white bg-dark-800/80 ${generalModule.color.replace('text-', 'border-')}`
                                : 'text-dark-400 hover:text-dark-200 hover:bg-dark-800/50 border-transparent'}
                        `}
                    >
                        <div className={`w-6 h-6 flex items-center justify-center shrink-0 rounded ${isGeneralSelected ? 'bg-dark-950' : ''}`}>
                            <generalModule.icon className={`w-4 h-4 ${isGeneralSelected ? generalModule.color : ''}`} />
                        </div>
                        <span className="truncate">{generalModule.name}</span>
                    </button>
                </div>
            )}

            {/* Sección Módulos */}
            <div className="border-t border-dark-800">
                <div className="flex items-center justify-between px-3 pt-3 pb-1">
                    <span className="text-[10px] font-semibold text-dark-500 uppercase tracking-wider">
                        Módulos
                    </span>
                    <button
                        onClick={onNavigateToModules}
                        className="text-dark-500 hover:text-siev-400 transition-colors"
                        title="Gestionar módulos"
                    >
                        <Plus className="w-3.5 h-3.5" />
                    </button>
                </div>

                <div className="flex flex-col">
                    {otherModules.map(mod => {
                        const isActive = activeStates[mod.id] || mod.isAlwaysVisible;
                        const isSelected = activeModuleId === mod.id && !selectedBatteryId;

                        if (!isActive) return null;

                        return (
                            <button
                                key={mod.id}
                                onClick={() => onModuleSelect(mod.id)}
                                className={`
                                    w-full flex items-center gap-2.5 px-3 py-2 text-sm font-medium transition-all text-left
                                    border-r-2
                                    ${isSelected
                                        ? `text-white bg-dark-800/80 ${mod.color.replace('text-', 'border-')}`
                                        : 'text-dark-400 hover:text-dark-200 hover:bg-dark-800/50 border-transparent'}
                                `}
                            >
                                <div className={`w-6 h-6 flex items-center justify-center shrink-0 rounded ${isSelected ? 'bg-dark-950' : ''}`}>
                                    {mod.imagePath ? (
                                        <img src={mod.imagePath} alt={mod.name} className="w-5 h-5 object-contain" />
                                    ) : (
                                        <mod.icon className={`w-4 h-4 ${isSelected ? mod.color : ''}`} />
                                    )}
                                </div>
                                <span className="truncate">{mod.name}</span>
                            </button>
                        );
                    })}
                </div>
            </div>

            <div className="border-t border-dark-800 mt-4">
                <div className="flex items-center justify-between px-3 pt-3 pb-1">
                    <span className="text-[10px] font-semibold text-dark-500 uppercase tracking-wider">
                        Baterías de pruebas
                    </span>
                    <button
                        onClick={onCreateBattery}
                        className="text-dark-500 hover:text-siev-400 transition-colors"
                        title="Crear batería de pruebas"
                    >
                        <Plus className="w-3.5 h-3.5" />
                    </button>
                </div>

                <div className="flex flex-col">
                    {batteries.map(battery => {
                        const isSelected = selectedBatteryId === battery.id;
                        return (
                            <button
                                key={battery.id}
                                onClick={() => onSelectBattery?.(battery.id)}
                                className={`
                                    w-full flex items-center gap-2.5 px-3 py-2 text-sm font-medium transition-all text-left
                                    border-r-2
                                    ${isSelected
                                        ? 'text-white bg-dark-800/80 border-siev-500'
                                        : 'text-dark-400 hover:text-dark-200 hover:bg-dark-800/50 border-transparent'}
                                `}
                            >
                                <div className={`w-6 h-6 flex items-center justify-center shrink-0 rounded text-[9px] font-bold ${isSelected ? 'bg-siev-600 text-white' : 'bg-dark-800 text-dark-400'}`}>
                                    {battery.shortName.slice(0, 3).toUpperCase()}
                                </div>
                                <span className="truncate">{battery.name}</span>
                            </button>
                        );
                    })}
                    {batteries.length === 0 && (
                        <div className="px-3 py-2 text-[11px] text-dark-600 italic">
                            Sin baterías
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
