import React, { useRef, useEffect } from 'react';

interface EditableFieldProps {
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
    label?: string;
}

export const EditableField: React.FC<EditableFieldProps> = ({
    value,
    onChange,
    placeholder = 'Escribir observaciones...',
    label,
}) => {
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (ref.current && ref.current.textContent !== value) {
            ref.current.textContent = value;
        }
    }, [value]);

    return (
        <div className="mt-2">
            {label && (
                <div className="text-xs font-medium text-gray-500 mb-1">{label}</div>
            )}
            <div
                ref={ref}
                contentEditable
                suppressContentEditableWarning
                onBlur={(e) => {
                    const text = e.currentTarget.textContent || '';
                    if (text !== value) onChange(text);
                }}
                className="min-h-[2em] px-3 py-2 text-sm text-gray-700 border border-gray-200 rounded
                    focus:outline-none focus:border-blue-300 focus:ring-1 focus:ring-blue-100
                    empty:before:content-[attr(data-placeholder)] empty:before:text-gray-400
                    whitespace-pre-wrap"
                data-placeholder={placeholder}
                style={{
                    // CSS :empty:before for placeholder
                }}
            />
            <style>{`
                [contenteditable]:empty:before {
                    content: attr(data-placeholder);
                    color: #9ca3af;
                    pointer-events: none;
                }
            `}</style>
        </div>
    );
};
