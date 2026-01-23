import React from 'react';

interface SettingsSectionProps {
    title: string;
    description?: string;
    icon?: React.ReactNode;
    children: React.ReactNode;
    className?: string;
}

export const SettingsSection: React.FC<SettingsSectionProps> = ({ title, description, icon, children, className = "" }) => {
    return (
        <div className={`space-y-3 ${className}`}>
            <div className="border-b border-dark-700 pb-1.5 flex items-center justify-between">
                <div>
                    <div className="flex items-center gap-2">
                        {icon && <span className="p-1.5 bg-dark-800 rounded-lg border border-dark-700">{icon}</span>}
                        <h3 className="text-lg font-bold text-white">{title}</h3>
                    </div>
                    {description && <p className="text-sm text-dark-400 mt-1">{description}</p>}
                </div>
            </div>
            <div className="space-y-4">
                {children}
            </div>
        </div>
    );
};
