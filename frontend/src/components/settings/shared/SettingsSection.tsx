import React from 'react';

interface SettingsSectionProps {
    title: string;
    description?: string;
    children: React.ReactNode;
    className?: string;
}

export const SettingsSection: React.FC<SettingsSectionProps> = ({ title, description, children, className = "" }) => {
    return (
        <div className={`space-y-4 ${className}`}>
            <div className="border-b border-dark-700 pb-2">
                <h3 className="text-lg font-bold text-white">{title}</h3>
                {description && <p className="text-sm text-dark-400 mt-1">{description}</p>}
            </div>
            <div className="space-y-6">
                {children}
            </div>
        </div>
    );
};
