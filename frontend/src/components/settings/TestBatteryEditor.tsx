import React, { useState } from 'react';
import { ChevronRight, ChevronLeft, Save, X, Eye, Target, MoveHorizontal, Activity, RotateCcw, Thermometer, PlayCircle, LucideIcon } from 'lucide-react';
import { TestBattery } from './ModuleSelector';

interface TestDefinition {
    id: string;
    title: string;
    icon: LucideIcon;
    color: string;
}

export const VNG_TESTS: TestDefinition[] = [
    { id: 'spontaneous', title: 'Nistagmo Espontáneo', icon: Eye, color: 'text-blue-400' },
    { id: 'calibration_gaze', title: 'Calibración Ocular', icon: Target, color: 'text-pink-400' },
    { id: 'saccades', title: 'Sacadas', icon: MoveHorizontal, color: 'text-green-400' },
    { id: 'pursuit', title: 'Seguimiento Pendular', icon: Activity, color: 'text-purple-400' },
    { id: 'positional', title: 'Pruebas Posicionales', icon: RotateCcw, color: 'text-orange-400' },
    { id: 'caloric', title: 'Pruebas Calóricas', icon: Thermometer, color: 'text-red-400' },
    { id: 'optokinetic', title: 'Optocinético / Full Field', icon: PlayCircle, color: 'text-cyan-400' },
];

interface TestBatteryEditorProps {
    onSave: (battery: TestBattery) => void;
    onCancel: () => void;
    editingBattery?: TestBattery | null;
}

export const TestBatteryEditor: React.FC<TestBatteryEditorProps> = ({ onSave, onCancel, editingBattery }) => {
    const [name, setName] = useState(editingBattery?.name ?? '');
    const [shortName, setShortName] = useState(editingBattery?.shortName ?? '');
    const [description, setDescription] = useState(editingBattery?.description ?? '');
    const [selectedIds, setSelectedIds] = useState<string[]>(editingBattery?.testIds ?? []);

    const availableTests = VNG_TESTS.filter(t => !selectedIds.includes(t.id));
    const selectedTests = selectedIds.map(id => VNG_TESTS.find(t => t.id === id)!).filter(Boolean);

    const addTest = (id: string) => {
        setSelectedIds(prev => [...prev, id]);
    };

    const removeTest = (id: string) => {
        setSelectedIds(prev => prev.filter(i => i !== id));
    };

    const moveUp = (index: number) => {
        if (index === 0) return;
        setSelectedIds(prev => {
            const next = [...prev];
            [next[index - 1], next[index]] = [next[index], next[index - 1]];
            return next;
        });
    };

    const moveDown = (index: number) => {
        if (index === selectedIds.length - 1) return;
        setSelectedIds(prev => {
            const next = [...prev];
            [next[index], next[index + 1]] = [next[index + 1], next[index]];
            return next;
        });
    };

    const handleSave = () => {
        if (!name.trim() || !shortName.trim() || selectedIds.length === 0) return;
        onSave({
            id: editingBattery?.id ?? crypto.randomUUID(),
            name: name.trim(),
            shortName: shortName.trim(),
            description: description.trim(),
            testIds: selectedIds,
        });
    };

    const canSave = name.trim().length > 0 && shortName.trim().length > 0 && selectedIds.length > 0;

    return (
        <div className="flex flex-col h-full">
            <div className="mb-4">
                <h3 className="text-lg font-semibold text-white mb-3">
                    {editingBattery ? 'Editar batería' : 'Nueva batería de pruebas'}
                </h3>

                <div className="grid grid-cols-[1fr_auto] gap-3 mb-3">
                    <div>
                        <label className="block text-xs text-dark-400 mb-1">Nombre</label>
                        <input
                            type="text"
                            value={name}
                            onChange={e => setName(e.target.value)}
                            placeholder="Ej: Batería vestibular completa"
                            className="w-full bg-dark-800 border border-dark-700 rounded px-3 py-2 text-sm text-white placeholder-dark-500 focus:outline-none focus:border-siev-500 transition-colors"
                            autoFocus
                        />
                    </div>
                    <div className="w-28">
                        <label className="block text-xs text-dark-400 mb-1">Siglas</label>
                        <input
                            type="text"
                            value={shortName}
                            onChange={e => setShortName(e.target.value.toUpperCase().slice(0, 5))}
                            placeholder="BVC"
                            maxLength={5}
                            className="w-full bg-dark-800 border border-dark-700 rounded px-3 py-2 text-sm text-white placeholder-dark-500 focus:outline-none focus:border-siev-500 transition-colors text-center font-bold tracking-wider"
                        />
                    </div>
                </div>

                <div>
                    <label className="block text-xs text-dark-400 mb-1">Descripción</label>
                    <input
                        type="text"
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                        placeholder="Ej: Incluye todas las pruebas del protocolo estándar"
                        className="w-full bg-dark-800 border border-dark-700 rounded px-3 py-2 text-sm text-white placeholder-dark-500 focus:outline-none focus:border-siev-500 transition-colors"
                    />
                </div>

                {/* Preview del logo */}
                {shortName.trim() && (
                    <div className="mt-3 flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-siev-600/20 border border-siev-500/30 flex items-center justify-center">
                            <span className="text-sm font-bold text-siev-400 tracking-wider">{shortName.slice(0, 3)}</span>
                        </div>
                        <span className="text-xs text-dark-500">Vista previa del logo</span>
                    </div>
                )}
            </div>

            <div className="flex-1 grid grid-cols-2 gap-4 min-h-0">
                {/* Columna izquierda: disponibles */}
                <div className="flex flex-col min-h-0">
                    <div className="text-xs font-semibold text-dark-400 uppercase tracking-wider mb-2">
                        Pruebas disponibles
                    </div>
                    <div className="flex-1 overflow-y-auto custom-scrollbar border border-dark-800 rounded bg-dark-900/50 p-1.5 space-y-1">
                        {availableTests.map(test => (
                            <button
                                key={test.id}
                                onClick={() => addTest(test.id)}
                                className="w-full flex items-center gap-2 px-2.5 py-2 rounded text-sm text-dark-300 hover:bg-dark-800 hover:text-white transition-colors group text-left"
                            >
                                <test.icon className={`w-4 h-4 ${test.color} shrink-0`} />
                                <span className="truncate flex-1">{test.title}</span>
                                <ChevronRight className="w-3.5 h-3.5 text-dark-600 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                            </button>
                        ))}
                        {availableTests.length === 0 && (
                            <div className="text-[11px] text-dark-600 italic px-2 py-3 text-center">
                                Todas las pruebas fueron agregadas
                            </div>
                        )}
                    </div>
                </div>

                {/* Columna derecha: seleccionadas */}
                <div className="flex flex-col min-h-0">
                    <div className="text-xs font-semibold text-dark-400 uppercase tracking-wider mb-2">
                        Pruebas seleccionadas ({selectedIds.length})
                    </div>
                    <div className="flex-1 overflow-y-auto custom-scrollbar border border-dark-800 rounded bg-dark-900/50 p-1.5 space-y-1">
                        {selectedTests.map((test, index) => (
                            <div
                                key={test.id}
                                className="flex items-center gap-1.5 px-2.5 py-2 rounded text-sm text-white bg-dark-800/60 group"
                            >
                                <span className="text-[10px] text-dark-500 w-4 text-center shrink-0">{index + 1}</span>
                                <test.icon className={`w-4 h-4 ${test.color} shrink-0`} />
                                <span className="truncate flex-1">{test.title}</span>
                                <div className="flex items-center gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button
                                        onClick={() => moveUp(index)}
                                        disabled={index === 0}
                                        className="p-0.5 text-dark-500 hover:text-white disabled:opacity-20 transition-colors"
                                        title="Subir"
                                    >
                                        <ChevronLeft className="w-3 h-3 rotate-90" />
                                    </button>
                                    <button
                                        onClick={() => moveDown(index)}
                                        disabled={index === selectedIds.length - 1}
                                        className="p-0.5 text-dark-500 hover:text-white disabled:opacity-20 transition-colors"
                                        title="Bajar"
                                    >
                                        <ChevronRight className="w-3 h-3 rotate-90" />
                                    </button>
                                    <button
                                        onClick={() => removeTest(test.id)}
                                        className="p-0.5 text-dark-500 hover:text-red-400 transition-colors ml-1"
                                        title="Quitar"
                                    >
                                        <X className="w-3 h-3" />
                                    </button>
                                </div>
                            </div>
                        ))}
                        {selectedTests.length === 0 && (
                            <div className="text-[11px] text-dark-600 italic px-2 py-3 text-center">
                                Haz clic en una prueba para agregarla
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Botones de acción */}
            <div className="flex items-center justify-end gap-3 mt-4 pt-3 border-t border-dark-800">
                <button
                    onClick={onCancel}
                    className="px-4 py-2 text-sm text-dark-400 hover:text-white transition-colors"
                >
                    Cancelar
                </button>
                <button
                    onClick={handleSave}
                    disabled={!canSave}
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-siev-600 hover:bg-siev-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded transition-colors"
                >
                    <Save className="w-4 h-4" />
                    Guardar batería
                </button>
            </div>
        </div>
    );
};
