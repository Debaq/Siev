import React from 'react';

interface HeaderSectionProps {
    institutionName: string;
    logoPath?: string;
    date: string;
}

export const HeaderSection: React.FC<HeaderSectionProps> = ({
    institutionName,
    logoPath,
    date
}) => {
    return (
        <div className="flex items-center justify-between border-b-2 border-gray-800 pb-4 mb-6">
            <div className="flex items-center gap-4">
                {logoPath && (
                    <img
                        src={logoPath}
                        alt="Logo"
                        className="h-16 w-auto object-contain"
                        onError={(e) => {
                            e.currentTarget.style.display = 'none';
                        }}
                    />
                )}
                <div>
                    <h1 className="text-xl font-bold text-gray-900">{institutionName}</h1>
                    <p className="text-sm text-gray-600">Informe de Videonistagmografía (VNG)</p>
                </div>
            </div>
            <div className="text-right text-sm text-gray-600">
                <p>Fecha del estudio:</p>
                <p className="font-semibold text-gray-800">{date}</p>
            </div>
        </div>
    );
};
