import React from 'react';

interface SignatureSectionProps {
    specialistName?: string;
}

export const SignatureSection: React.FC<SignatureSectionProps> = ({ specialistName }) => {
    return (
        <div className="mt-8 pt-8 border-t border-gray-300">
            <div className="flex justify-end">
                <div className="w-64 text-center">
                    <div className="border-b border-gray-400 mb-2 h-16"></div>
                    <div className="text-sm font-medium text-gray-800">
                        {specialistName || 'Profesional Responsable'}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                        Firma y Sello
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div className="mt-8 pt-4 border-t border-gray-200 text-center text-xs text-gray-400">
                <p>Este informe ha sido generado automáticamente por el sistema SIEV.</p>
                <p>Los resultados deben ser interpretados en el contexto clínico del paciente.</p>
            </div>
        </div>
    );
};
