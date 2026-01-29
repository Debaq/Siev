import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Check, X, RotateCcw, Eye } from 'lucide-react';
import { emit } from '@tauri-apps/api/event';
import { useWebSocket } from '../../contexts/WebSocketContext';

interface CalibrationPoint {
    id: string;
    label: string;
    x: number;  // -1 to 1 normalized position
    y: number;  // -1 to 1 normalized position
    captured: boolean;
    eyeDataRight?: { x: number; y: number };
    eyeDataLeft?: { x: number; y: number };
}

interface Props {
    patternType: '3_points' | '5_points' | '9_points';
    horizontalAngle: number;  // degrees
    verticalAngle: number;    // degrees
    patientDistance: number;  // cm (default 150)
    onComplete: (calibrationData: CalibrationResult) => void;
    onCancel: () => void;
}

export interface CalibrationResult {
    points: {
        id: string;
        angleX: number;
        angleY: number;
        pixelRight: { x: number; y: number };
        pixelLeft: { x: number; y: number };
    }[];
    patientDistance: number;
    timestamp: number;
}

// Generate calibration points based on pattern type
function generatePoints(
    patternType: '3_points' | '5_points' | '9_points'
): CalibrationPoint[] {
    const points: CalibrationPoint[] = [];

    // Center point is always first
    points.push({ id: 'C', label: 'Centro', x: 0, y: 0, captured: false });

    if (patternType === '3_points') {
        // Horizontal only: Left, Center, Right
        points.push({ id: 'L', label: 'Izquierda', x: -1, y: 0, captured: false });
        points.push({ id: 'R', label: 'Derecha', x: 1, y: 0, captured: false });
    } else if (patternType === '5_points') {
        // Cross pattern
        points.push({ id: 'L', label: 'Izquierda', x: -1, y: 0, captured: false });
        points.push({ id: 'R', label: 'Derecha', x: 1, y: 0, captured: false });
        points.push({ id: 'U', label: 'Arriba', x: 0, y: -1, captured: false });
        points.push({ id: 'D', label: 'Abajo', x: 0, y: 1, captured: false });
    } else if (patternType === '9_points') {
        // 3x3 Grid
        points.push({ id: 'TL', label: 'Sup-Izq', x: -1, y: -1, captured: false });
        points.push({ id: 'T', label: 'Superior', x: 0, y: -1, captured: false });
        points.push({ id: 'TR', label: 'Sup-Der', x: 1, y: -1, captured: false });
        points.push({ id: 'L', label: 'Izquierda', x: -1, y: 0, captured: false });
        points.push({ id: 'R', label: 'Derecha', x: 1, y: 0, captured: false });
        points.push({ id: 'BL', label: 'Inf-Izq', x: -1, y: 1, captured: false });
        points.push({ id: 'B', label: 'Inferior', x: 0, y: 1, captured: false });
        points.push({ id: 'BR', label: 'Inf-Der', x: 1, y: 1, captured: false });
    }

    return points;
}

export const ManualCalibration: React.FC<Props> = ({
    patternType,
    horizontalAngle,
    verticalAngle,
    patientDistance,
    onComplete,
    onCancel
}) => {
    const { addListener, removeListener } = useWebSocket();
    const [points, setPoints] = useState<CalibrationPoint[]>(() =>
        generatePoints(patternType)
    );
    const [activePoint, setActivePoint] = useState<string | null>(null);
    const [lastEyeData, setLastEyeData] = useState<{
        left: { x: number; y: number } | null;
        right: { x: number; y: number } | null;
        timestamp: number;
    }>({ left: null, right: null, timestamp: 0 });

    // Video frame for ROI display
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const latestFrameRef = useRef<Blob | string | null>(null);

    // Listen to eye data from WebSocket
    useEffect(() => {
        const handleEyeData = (data: any) => {
            const wsData = data as {
                left: number[] | null;
                right: number[] | null;
                timestamp: number;
            };

            setLastEyeData({
                left: wsData.left ? { x: wsData.left[0], y: wsData.left[1] } : null,
                right: wsData.right ? { x: wsData.right[0], y: wsData.right[1] } : null,
                timestamp: wsData.timestamp
            });
        };

        addListener('eye_data', handleEyeData);
        return () => removeListener('eye_data', handleEyeData);
    }, [addListener, removeListener]);

    // Listen to video frames for ROI display
    useEffect(() => {
        const handleFrame = (data: Blob | string) => {
            latestFrameRef.current = data;
        };

        addListener('video_frame', handleFrame);

        // Render loop for ROI
        let animationFrame: number;
        const renderROI = async () => {
            if (canvasRef.current && latestFrameRef.current) {
                const canvas = canvasRef.current;
                const ctx = canvas.getContext('2d');
                if (ctx) {
                    try {
                        if (latestFrameRef.current instanceof Blob) {
                            const bitmap = await createImageBitmap(latestFrameRef.current);
                            // Draw scaled to fit canvas
                            ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
                            bitmap.close();
                        }
                    } catch (e) {
                        // Ignore frame errors
                    }
                }
            }
            animationFrame = requestAnimationFrame(renderROI);
        };

        animationFrame = requestAnimationFrame(renderROI);

        return () => {
            removeListener('video_frame', handleFrame);
            cancelAnimationFrame(animationFrame);
        };
    }, [addListener, removeListener]);

    // Handle point click - capture current eye position
    const handlePointClick = useCallback((pointId: string) => {
        if (!lastEyeData.left && !lastEyeData.right) {
            console.warn('No eye data available');
            return;
        }

        setPoints(prev => prev.map(p => {
            if (p.id === pointId) {
                return {
                    ...p,
                    captured: true,
                    eyeDataRight: lastEyeData.right || undefined,
                    eyeDataLeft: lastEyeData.left || undefined
                };
            }
            return p;
        }));

        setActivePoint(pointId);

        // Brief visual feedback
        setTimeout(() => setActivePoint(null), 300);
    }, [lastEyeData]);

    // Reset a single point
    const handleResetPoint = useCallback((pointId: string) => {
        setPoints(prev => prev.map(p => {
            if (p.id === pointId) {
                return { ...p, captured: false, eyeDataRight: undefined, eyeDataLeft: undefined };
            }
            return p;
        }));
    }, []);

    // Reset all points
    const handleResetAll = useCallback(() => {
        setPoints(generatePoints(patternType));
    }, [patternType]);

    // Check if all points captured
    const allCaptured = points.every(p => p.captured);
    const capturedCount = points.filter(p => p.captured).length;

    // Complete calibration
    const handleComplete = useCallback(async () => {
        if (!allCaptured) return;

        const result: CalibrationResult = {
            points: points.map(p => ({
                id: p.id,
                angleX: p.x * horizontalAngle,       // left(-) right(+)
                angleY: -(p.y * verticalAngle),       // up(+) down(-)
                pixelRight: p.eyeDataRight || { x: 0, y: 0 },
                pixelLeft: p.eyeDataLeft || { x: 0, y: 0 }
            })),
            patientDistance,
            timestamp: Date.now()
        };

        // Emit calibration complete event
        await emit('manual_calibration_complete', result);

        onComplete(result);
    }, [allCaptured, points, horizontalAngle, verticalAngle, patientDistance, onComplete]);

    // Calculate point position on screen
    const getPointScreenPosition = (point: CalibrationPoint) => {
        // Use percentage of screen, with some margin
        const marginX = 15; // % from edge
        const marginY = 15;

        const x = 50 + (point.x * (50 - marginX));
        const y = 50 + (point.y * (50 - marginY));

        return { x: `${x}%`, y: `${y}%` };
    };

    return (
        <div className="h-screen w-screen bg-black text-white relative overflow-hidden cursor-default">
            {/* Header with instructions */}
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 bg-black/80 backdrop-blur-sm border border-white/10 rounded-xl px-6 py-3 text-center">
                <h2 className="text-lg font-bold mb-1">Calibracion Manual VNG</h2>
                <p className="text-sm text-gray-400">
                    Indique al paciente que mire cada punto. Haga clic en el punto cuando el paciente lo este mirando.
                </p>
                <div className="mt-2 text-xs text-gray-500">
                    Patron: {patternType.replace('_', ' ')} | Angulos: {horizontalAngle}° H / {verticalAngle}° V | Distancia: {patientDistance}cm
                </div>
            </div>

            {/* Progress indicator */}
            <div className="absolute top-4 right-4 z-20 bg-black/80 backdrop-blur-sm border border-white/10 rounded-lg px-4 py-2">
                <div className="text-xs text-gray-400 mb-1">Progreso</div>
                <div className="text-lg font-bold">
                    <span className={capturedCount === points.length ? 'text-green-400' : 'text-white'}>
                        {capturedCount}
                    </span>
                    <span className="text-gray-500"> / {points.length}</span>
                </div>
            </div>

            {/* ROI Preview - Top Left */}
            <div className="absolute top-4 left-4 z-20 bg-black/90 border border-white/20 rounded-lg overflow-hidden">
                <div className="px-2 py-1 bg-white/5 border-b border-white/10 flex items-center gap-2">
                    <Eye className="w-3 h-3 text-cyan-400" />
                    <span className="text-[10px] font-bold text-gray-400">SEGUIMIENTO OCULAR</span>
                </div>
                <canvas
                    ref={canvasRef}
                    width={320}
                    height={120}
                    className="block"
                />
                {/* Eye position overlay */}
                <div className="px-2 py-1 bg-black/50 text-[9px] font-mono flex gap-4">
                    <div className="text-red-400">
                        OD: {lastEyeData.right ? `(${lastEyeData.right.x.toFixed(1)}, ${lastEyeData.right.y.toFixed(1)})` : '--'}
                    </div>
                    <div className="text-cyan-400">
                        OI: {lastEyeData.left ? `(${lastEyeData.left.x.toFixed(1)}, ${lastEyeData.left.y.toFixed(1)})` : '--'}
                    </div>
                </div>
            </div>

            {/* Calibration Points */}
            {points.map(point => {
                const pos = getPointScreenPosition(point);
                const isActive = activePoint === point.id;

                return (
                    <button
                        key={point.id}
                        onClick={() => handlePointClick(point.id)}
                        onContextMenu={(e) => {
                            e.preventDefault();
                            handleResetPoint(point.id);
                        }}
                        style={{ left: pos.x, top: pos.y }}
                        className={`absolute -translate-x-1/2 -translate-y-1/2 group transition-all duration-200 ${
                            isActive ? 'scale-125' : ''
                        }`}
                    >
                        {/* Target circle */}
                        <div className={`relative w-12 h-12 rounded-full border-2 flex items-center justify-center transition-all ${
                            point.captured
                                ? 'bg-green-500/20 border-green-500'
                                : 'bg-red-500/20 border-red-500 hover:bg-red-500/40 hover:scale-110'
                        }`}>
                            {/* Inner dot */}
                            <div className={`w-3 h-3 rounded-full ${
                                point.captured ? 'bg-green-500' : 'bg-red-500'
                            }`} />

                            {/* Check mark if captured */}
                            {point.captured && (
                                <div className="absolute -top-1 -right-1 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center">
                                    <Check className="w-3 h-3 text-white" />
                                </div>
                            )}
                        </div>

                        {/* Label */}
                        <div className={`absolute top-full left-1/2 -translate-x-1/2 mt-2 text-xs font-bold whitespace-nowrap ${
                            point.captured ? 'text-green-400' : 'text-gray-400'
                        }`}>
                            {point.label}
                        </div>

                        {/* Tooltip on hover */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                            <div className="bg-black/90 border border-white/20 rounded px-2 py-1 text-[10px] whitespace-nowrap">
                                {point.captured ? 'Clic derecho para resetear' : 'Clic para capturar'}
                            </div>
                        </div>
                    </button>
                );
            })}

            {/* Crosshair overlay for visual reference */}
            <div className="absolute inset-0 pointer-events-none">
                {/* Horizontal line */}
                <div className="absolute top-1/2 left-0 right-0 h-px bg-white/10" />
                {/* Vertical line */}
                <div className="absolute left-1/2 top-0 bottom-0 w-px bg-white/10" />
            </div>

            {/* Bottom controls */}
            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex gap-3">
                <button
                    onClick={handleResetAll}
                    className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 border border-white/20 rounded-lg transition-colors"
                >
                    <RotateCcw className="w-4 h-4" />
                    Reiniciar Todo
                </button>

                <button
                    onClick={onCancel}
                    className="flex items-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-300 rounded-lg transition-colors"
                >
                    <X className="w-4 h-4" />
                    Cancelar
                </button>

                <button
                    onClick={handleComplete}
                    disabled={!allCaptured}
                    className={`flex items-center gap-2 px-6 py-2 rounded-lg font-bold transition-all ${
                        allCaptured
                            ? 'bg-green-600 hover:bg-green-500 text-white shadow-lg shadow-green-900/30'
                            : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                    }`}
                >
                    <Check className="w-4 h-4" />
                    Completar Calibracion
                </button>
            </div>

            {/* Keyboard shortcuts hint */}
            <div className="absolute bottom-4 right-4 text-[10px] text-gray-600">
                ESC para cancelar
            </div>
        </div>
    );
};
