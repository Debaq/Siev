import React from 'react';
import { Target, Crosshair, Clock, Ruler } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsField } from '../shared/SettingsField';
import { AppConfig } from '../../../types/config';

interface CalibrationTabProps {
    config: AppConfig;
    updateConfig: (path: string, value: any) => void;
}

export const CalibrationTab: React.FC<CalibrationTabProps> = ({ config, updateConfig }) => {
    const calibration = config.vng.calibration;

    return (
        <div className="space-y-6 animate-fade-in">
            <SettingsSection
                title="Protocolo de Calibración"
                description="Configure el patrón y parámetros para la calibración del sistema VNG."
                icon={<Target className="w-4 h-4 text-siev-500" />}
            >
                <SettingsField label="Patrón de Puntos">
                    <select
                        className="select h-9 py-1 text-sm"
                        value={calibration.pattern_type}
                        onChange={e => updateConfig('vng.calibration.pattern_type', e.target.value)}
                    >
                        <option value="3_points">3 Puntos (Horizontal)</option>
                        <option value="5_points">5 Puntos (Cruz)</option>
                        <option value="9_points">9 Puntos (Rejilla)</option>
                    </select>
                </SettingsField>

                {/* Pattern Preview */}
                <div className="p-3 bg-dark-800/50 rounded-lg border border-dark-700">
                    <div className="flex items-center gap-2 mb-2 text-[10px] text-dark-400">
                        <Crosshair className="w-3 h-3" />
                        <span>Vista previa del patrón</span>
                    </div>
                    <div className="relative w-full aspect-video bg-dark-900 rounded border border-dark-600 flex items-center justify-center">
                        <CalibrationPatternPreview
                            pattern={calibration.pattern_type}
                            horizontalAngle={calibration.horizontal_angle}
                            verticalAngle={calibration.vertical_angle}
                        />
                    </div>
                </div>
            </SettingsSection>

            <SettingsSection
                title="Parámetros de Ángulos"
                description="Defina los ángulos de excursión ocular para los puntos de calibración."
                icon={<Ruler className="w-4 h-4 text-cyan-500" />}
            >
                <div className="grid grid-cols-2 gap-4">
                    <SettingsField label="Ángulo Horizontal (Grados)" description="Normalmente 15° o 30°">
                        <input
                            type="number"
                            className="input h-9 text-sm"
                            min="5"
                            max="45"
                            value={calibration.horizontal_angle}
                            onChange={e => updateConfig('vng.calibration.horizontal_angle', Number(e.target.value))}
                        />
                    </SettingsField>
                    <SettingsField label="Ángulo Vertical (Grados)" description="Normalmente 10° o 20°">
                        <input
                            type="number"
                            className="input h-9 text-sm"
                            min="5"
                            max="30"
                            value={calibration.vertical_angle}
                            onChange={e => updateConfig('vng.calibration.vertical_angle', Number(e.target.value))}
                        />
                    </SettingsField>
                </div>
            </SettingsSection>

            <SettingsSection
                title="Tiempos y Distancia"
                description="Configure la duración de la fijación y la distancia del paciente."
                icon={<Clock className="w-4 h-4 text-orange-500" />}
            >
                <div className="grid grid-cols-2 gap-4">
                    <SettingsField label="Duración por Punto (seg)" description="Tiempo de fijación en cada punto">
                        <input
                            type="number"
                            step="0.5"
                            min="1"
                            max="10"
                            className="input h-9 text-sm"
                            value={calibration.point_duration}
                            onChange={e => updateConfig('vng.calibration.point_duration', Number(e.target.value))}
                        />
                    </SettingsField>
                    <SettingsField label="Distancia Paciente (cm)" description="Distancia del paciente a la pantalla">
                        <input
                            type="number"
                            min="30"
                            max="150"
                            className="input h-9 text-sm"
                            value={calibration.patient_distance_cm}
                            onChange={e => updateConfig('vng.calibration.patient_distance_cm', Number(e.target.value))}
                        />
                    </SettingsField>
                </div>
            </SettingsSection>
        </div>
    );
};

// Preview component for calibration pattern
interface PatternPreviewProps {
    pattern: string;
    horizontalAngle: number;
    verticalAngle: number;
}

const CalibrationPatternPreview: React.FC<PatternPreviewProps> = ({ pattern, horizontalAngle, verticalAngle }) => {
    const points: { x: number; y: number; label: string }[] = [];

    // Center point always present
    points.push({ x: 50, y: 50, label: 'C' });

    if (pattern === '3_points') {
        // Horizontal only
        points.push({ x: 50 - horizontalAngle, y: 50, label: 'L' });
        points.push({ x: 50 + horizontalAngle, y: 50, label: 'R' });
    } else if (pattern === '5_points') {
        // Cross pattern
        points.push({ x: 50 - horizontalAngle, y: 50, label: 'L' });
        points.push({ x: 50 + horizontalAngle, y: 50, label: 'R' });
        points.push({ x: 50, y: 50 - verticalAngle, label: 'U' });
        points.push({ x: 50, y: 50 + verticalAngle, label: 'D' });
    } else if (pattern === '9_points') {
        // Grid pattern
        [-1, 0, 1].forEach(col => {
            [-1, 0, 1].forEach(row => {
                if (col !== 0 || row !== 0) {
                    points.push({
                        x: 50 + col * horizontalAngle,
                        y: 50 + row * verticalAngle,
                        label: ''
                    });
                }
            });
        });
    }

    return (
        <svg viewBox="0 0 100 100" className="w-full h-full">
            {/* Grid lines */}
            <line x1="0" y1="50" x2="100" y2="50" stroke="#334155" strokeWidth="0.5" strokeDasharray="2,2" />
            <line x1="50" y1="0" x2="50" y2="100" stroke="#334155" strokeWidth="0.5" strokeDasharray="2,2" />

            {/* Angle indicators */}
            <text x="50" y="8" textAnchor="middle" fill="#64748b" fontSize="4">{verticalAngle}°</text>
            <text x="92" y="52" textAnchor="middle" fill="#64748b" fontSize="4">{horizontalAngle}°</text>

            {/* Points */}
            {points.map((point, i) => (
                <g key={i}>
                    <circle
                        cx={point.x}
                        cy={point.y}
                        r={i === 0 ? 3 : 2}
                        fill={i === 0 ? '#14b8a6' : '#f43f5e'}
                        opacity={0.9}
                    />
                    {point.label && (
                        <text
                            x={point.x}
                            y={point.y + 6}
                            textAnchor="middle"
                            fill="#94a3b8"
                            fontSize="3"
                        >
                            {point.label}
                        </text>
                    )}
                </g>
            ))}
        </svg>
    );
};
