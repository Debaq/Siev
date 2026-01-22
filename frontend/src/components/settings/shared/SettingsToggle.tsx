import React from 'react';

interface SettingsToggleProps {
    checked: boolean;
    onChange: (checked: boolean) => void;
    disabled?: boolean;
}

export const SettingsToggle: React.FC<SettingsToggleProps> = ({ checked, onChange, disabled = false }) => {
    return (
        <label className={`relative inline-flex items-center ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}>
            <input 
                type="checkbox" 
                className="sr-only peer"
                checked={checked}
                disabled={disabled}
                onChange={e => onChange(e.target.checked)}
            />
            <div className="w-10 h-5 bg-dark-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-siev-600"></div>
        </label>
    );
};
