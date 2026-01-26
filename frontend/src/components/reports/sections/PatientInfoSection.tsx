import React from 'react';
import { PatientReportData, SessionReportData } from '../../../types/vng';

interface PatientInfoSectionProps {
    patient: PatientReportData;
    session: SessionReportData;
}

export const PatientInfoSection: React.FC<PatientInfoSectionProps> = ({
    patient,
    session
}) => {
    return (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3">
                Datos del Paciente
            </h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                    <span className="text-gray-500">Nombre:</span>
                    <span className="ml-2 font-medium text-gray-900">{patient.full_name}</span>
                </div>
                {patient.dni && (
                    <div>
                        <span className="text-gray-500">DNI:</span>
                        <span className="ml-2 font-medium text-gray-900">{patient.dni}</span>
                    </div>
                )}
                {patient.age && (
                    <div>
                        <span className="text-gray-500">Edad:</span>
                        <span className="ml-2 font-medium text-gray-900">{patient.age} años</span>
                    </div>
                )}
                {patient.gender && (
                    <div>
                        <span className="text-gray-500">Género:</span>
                        <span className="ml-2 font-medium text-gray-900">
                            {patient.gender === 'M' ? 'Masculino' : patient.gender === 'F' ? 'Femenino' : patient.gender}
                        </span>
                    </div>
                )}
                {session.specialist_name && (
                    <div>
                        <span className="text-gray-500">Especialista:</span>
                        <span className="ml-2 font-medium text-gray-900">{session.specialist_name}</span>
                    </div>
                )}
                {session.description && (
                    <div className="col-span-2">
                        <span className="text-gray-500">Motivo de consulta:</span>
                        <span className="ml-2 font-medium text-gray-900">{session.description}</span>
                    </div>
                )}
            </div>
        </div>
    );
};
