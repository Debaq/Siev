import React from 'react';

interface SettingsSectionProps {
    title: string;
    description?: string;
    children: React.ReactNode;
    className?: string;
}

export const SettingsSection: React.FC<SettingsSectionProps> = ({ title, description, children, className = "" }) => {
    return (
        <div className={`space-y-3 ${className}`}>
            <div className="border-b border-dark-700 pb-1.5">
                <h3 className="text-lg font-bold text-white">{title}</h3>
                {description && <p className="text-sm text-dark-400 mt-0.5">{description}</p>}
            </div>
            <div className="space-y-4">
                {children}
            </div>
        </div>
    );
};
