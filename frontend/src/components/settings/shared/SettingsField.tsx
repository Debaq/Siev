import React from 'react';

interface SettingsFieldProps {
    label: string;
    description?: string;
    children: React.ReactNode;
    className?: string;
    inline?: boolean;
}

export const SettingsField: React.FC<SettingsFieldProps> = ({ 
    label, 
    description, 
    children, 
    className = "",
    inline = false 
}) => {
    if (inline) {
        return (
            <div className={`flex items-center justify-between gap-4 ${className}`}>
                <div className="flex-1">
                    <label className="block text-sm font-medium text-dark-200">{label}</label>
                    {description && <p className="text-xs text-dark-500 mt-0.5">{description}</p>}
                </div>
                <div className="shrink-0">
                    {children}
                </div>
            </div>
        );
    }

    return (
        <div className={`space-y-1 ${className}`}>
            <label className="block text-sm font-medium text-dark-200">{label}</label>
            {children}
            {description && <p className="text-xs text-dark-500">{description}</p>}
        </div>
    );
};
