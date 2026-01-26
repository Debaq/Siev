import React, { useState, useCallback } from 'react';
import { GripVertical, Eye, EyeOff } from 'lucide-react';
import { ReportSection } from '../../../types/config';

interface ReportSectionEditorProps {
    sections: ReportSection[];
    onChange: (sections: ReportSection[]) => void;
}

export const ReportSectionEditor: React.FC<ReportSectionEditorProps> = ({ sections, onChange }) => {
    const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
    const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

    const sortedSections = [...sections].sort((a, b) => a.order - b.order);

    const handleToggle = useCallback((id: string) => {
        const updated = sections.map(s =>
            s.id === id ? { ...s, enabled: !s.enabled } : s
        );
        onChange(updated);
    }, [sections, onChange]);

    const handleDragStart = (e: React.DragEvent, index: number) => {
        setDraggedIndex(index);
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', index.toString());
    };

    const handleDragOver = (e: React.DragEvent, index: number) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        setDragOverIndex(index);
    };

    const handleDragLeave = () => {
        setDragOverIndex(null);
    };

    const handleDrop = (e: React.DragEvent, dropIndex: number) => {
        e.preventDefault();
        if (draggedIndex === null || draggedIndex === dropIndex) {
            setDraggedIndex(null);
            setDragOverIndex(null);
            return;
        }

        const newSections = [...sortedSections];
        const [removed] = newSections.splice(draggedIndex, 1);
        newSections.splice(dropIndex, 0, removed);

        // Update order values
        const reordered = newSections.map((s, idx) => ({ ...s, order: idx }));
        onChange(reordered);

        setDraggedIndex(null);
        setDragOverIndex(null);
    };

    const handleDragEnd = () => {
        setDraggedIndex(null);
        setDragOverIndex(null);
    };

    return (
        <div className="space-y-1">
            {sortedSections.map((section, index) => (
                <div
                    key={section.id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, index)}
                    onDragOver={(e) => handleDragOver(e, index)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, index)}
                    onDragEnd={handleDragEnd}
                    className={`
                        flex items-center gap-3 p-2 rounded-lg transition-all cursor-move
                        ${draggedIndex === index ? 'opacity-50 scale-95' : ''}
                        ${dragOverIndex === index ? 'bg-siev-500/20 border-siev-500' : 'bg-dark-800/50 border-transparent'}
                        ${section.enabled ? 'border border-dark-700' : 'border border-dark-800 opacity-60'}
                        hover:bg-dark-700/50
                    `}
                >
                    {/* Drag Handle */}
                    <div className="text-dark-500 hover:text-dark-300">
                        <GripVertical className="w-4 h-4" />
                    </div>

                    {/* Order Number */}
                    <div className={`
                        w-5 h-5 rounded text-[10px] font-medium flex items-center justify-center
                        ${section.enabled ? 'bg-siev-600 text-white' : 'bg-dark-700 text-dark-500'}
                    `}>
                        {index + 1}
                    </div>

                    {/* Section Label */}
                    <div className={`flex-1 text-sm ${section.enabled ? 'text-dark-200' : 'text-dark-500'}`}>
                        {section.label}
                    </div>

                    {/* Toggle Button */}
                    <button
                        onClick={() => handleToggle(section.id)}
                        className={`
                            p-1.5 rounded transition-colors
                            ${section.enabled
                                ? 'text-siev-400 hover:bg-siev-500/20'
                                : 'text-dark-500 hover:bg-dark-600'
                            }
                        `}
                        title={section.enabled ? 'Ocultar sección' : 'Mostrar sección'}
                    >
                        {section.enabled ? (
                            <Eye className="w-4 h-4" />
                        ) : (
                            <EyeOff className="w-4 h-4" />
                        )}
                    </button>
                </div>
            ))}

            {/* Summary */}
            <div className="pt-2 mt-2 border-t border-dark-700 text-xs text-dark-500 flex justify-between">
                <span>
                    {sortedSections.filter(s => s.enabled).length} de {sortedSections.length} secciones habilitadas
                </span>
                <span className="text-dark-600">
                    Arrastra para reordenar
                </span>
            </div>
        </div>
    );
};
