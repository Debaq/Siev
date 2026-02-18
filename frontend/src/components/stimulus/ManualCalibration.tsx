import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Check, X, RotateCcw, Eye } from 'lucide-react';
import { emit } from '@tauri-apps/api/event';
import { useWebSocket } from '../../contexts/WebSocketContext';

// ─── Configuracion de captura ────────────────────────────────────────────────

const CAPTURE_CONFIG = {
    COUNTDOWN_SECONDS: 3,          // Pre-captura: 3, 2, 1
    COUNTDOWN_INTERVAL_MS: 500,    // Intervalo entre numeros del countdown
    SAMPLING_DURATION_MS: 1000,    // Duracion de captura de muestras
    MIN_SAMPLES_REQUIRED: 10,      // Minimo de muestras totales
    MIN_SAMPLES_AFTER_FILTER: 7,   // Minimo tras filtrado IQR
    IQR_FACTOR: 1.5,               // Factor para rechazo de outliers
    QUALITY_EXCELLENT: 80,         // Umbral para calidad excelente
    RESULT_DISPLAY_MS: 1500,       // Tiempo que se muestra el resultado
    PROGRESS_RING_RADIUS: 30,      // Radio del anillo SVG
    PROGRESS_RING_STROKE: 3,       // Grosor del anillo
} as const;

// ─── Interfaces ──────────────────────────────────────────────────────────────

interface EyeSample {
    left: { x: number; y: number } | null;
    right: { x: number; y: number } | null;
    timestamp: number;
}

type CapturePhase = 'idle' | 'countdown' | 'sampling' | 'result';
type CaptureQuality = 'success' | 'warning' | 'failed';

interface CaptureResult {
    quality: CaptureQuality;
    qualityScore: number;          // 0-100
    medianLeft: { x: number; y: number } | null;
    medianRight: { x: number; y: number } | null;
    totalSamples: number;
    usedSamples: number;
}

interface CaptureState {
    phase: CapturePhase;
    pointId: string | null;
    countdownValue: number;        // 3, 2, 1
    samplingProgress: number;      // 0.0 - 1.0
    result: CaptureResult | null;
}

interface CalibrationPoint {
    id: string;
    label: string;
    x: number;
    y: number;
    captured: boolean;
    eyeDataRight?: { x: number; y: number };
    eyeDataLeft?: { x: number; y: number };
    captureQuality?: CaptureQuality;
    qualityScore?: number;
}

interface Props {
    patternType: '3_points' | '5_points' | '9_points';
    horizontalAngle: number;
    verticalAngle: number;
    patientDistance: number;
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

// ─── Algoritmo estadistico ───────────────────────────────────────────────────

function median(sorted: number[]): number {
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 !== 0
        ? sorted[mid]
        : (sorted[mid - 1] + sorted[mid]) / 2;
}

function stdDev(values: number[], med: number): number {
    const squaredDiffs = values.map(v => (v - med) ** 2);
    return Math.sqrt(squaredDiffs.reduce((a, b) => a + b, 0) / values.length);
}

interface AxisAnalysis {
    median: number;
    stdDev: number;
    usedCount: number;
    totalCount: number;
}

function analyzeAxis(values: number[]): AxisAnalysis | null {
    if (values.length < CAPTURE_CONFIG.MIN_SAMPLES_REQUIRED) return null;

    const sorted = [...values].sort((a, b) => a - b);
    const q1 = median(sorted.slice(0, Math.floor(sorted.length / 2)));
    const q3 = median(sorted.slice(Math.ceil(sorted.length / 2)));
    const iqr = q3 - q1;
    const lower = q1 - CAPTURE_CONFIG.IQR_FACTOR * iqr;
    const upper = q3 + CAPTURE_CONFIG.IQR_FACTOR * iqr;

    const filtered = sorted.filter(v => v >= lower && v <= upper);

    if (filtered.length < CAPTURE_CONFIG.MIN_SAMPLES_AFTER_FILTER) return null;

    const med = median(filtered);
    const sd = stdDev(filtered, med);

    return { median: med, stdDev: sd, usedCount: filtered.length, totalCount: values.length };
}

function analyzeCaptureSamples(samples: EyeSample[]): CaptureResult {
    const leftXValues: number[] = [];
    const leftYValues: number[] = [];
    const rightXValues: number[] = [];
    const rightYValues: number[] = [];

    for (const s of samples) {
        if (s.left) { leftXValues.push(s.left.x); leftYValues.push(s.left.y); }
        if (s.right) { rightXValues.push(s.right.x); rightYValues.push(s.right.y); }
    }

    const hasLeft = leftXValues.length >= CAPTURE_CONFIG.MIN_SAMPLES_REQUIRED;
    const hasRight = rightXValues.length >= CAPTURE_CONFIG.MIN_SAMPLES_REQUIRED;

    if (!hasLeft && !hasRight) {
        return { quality: 'failed', qualityScore: 0, medianLeft: null, medianRight: null, totalSamples: samples.length, usedSamples: 0 };
    }

    let medianLeft: { x: number; y: number } | null = null;
    let medianRight: { x: number; y: number } | null = null;
    let totalUsed = 0;
    let totalOriginal = 0;
    let combinedStdDev = 0;
    let axisCount = 0;

    if (hasLeft) {
        const lx = analyzeAxis(leftXValues);
        const ly = analyzeAxis(leftYValues);
        if (lx && ly) {
            medianLeft = { x: lx.median, y: ly.median };
            totalUsed += Math.min(lx.usedCount, ly.usedCount);
            totalOriginal += Math.min(lx.totalCount, ly.totalCount);
            combinedStdDev += lx.stdDev + ly.stdDev;
            axisCount += 2;
        }
    }

    if (hasRight) {
        const rx = analyzeAxis(rightXValues);
        const ry = analyzeAxis(rightYValues);
        if (rx && ry) {
            medianRight = { x: rx.median, y: ry.median };
            totalUsed += Math.min(rx.usedCount, ry.usedCount);
            totalOriginal += Math.min(rx.totalCount, ry.totalCount);
            combinedStdDev += rx.stdDev + ry.stdDev;
            axisCount += 2;
        }
    }

    if (!medianLeft && !medianRight) {
        return { quality: 'failed', qualityScore: 0, medianLeft: null, medianRight: null, totalSamples: samples.length, usedSamples: 0 };
    }

    // Calidad basada en stdDev promedio y % muestras conservadas
    const avgStdDev = axisCount > 0 ? combinedStdDev / axisCount : 999;
    const retentionRatio = totalOriginal > 0 ? totalUsed / totalOriginal : 0;

    // stdDev < 2px => excelente, > 10px => malo
    const stdScore = Math.max(0, Math.min(100, 100 - (avgStdDev - 2) * (100 / 8)));
    // retentionRatio 1.0 => +0, 0.5 => -25
    const retentionPenalty = (1 - retentionRatio) * 50;

    const qualityScore = Math.round(Math.max(0, Math.min(100, stdScore - retentionPenalty)));

    let quality: CaptureQuality;
    if (qualityScore >= CAPTURE_CONFIG.QUALITY_EXCELLENT) {
        quality = 'success';
    } else if (medianLeft || medianRight) {
        quality = 'warning';
    } else {
        quality = 'failed';
    }

    return { quality, qualityScore, medianLeft, medianRight, totalSamples: samples.length, usedSamples: totalUsed };
}

// ─── Componente de anillo de progreso ────────────────────────────────────────

const CaptureProgressRing: React.FC<{ progress: number; phase: CapturePhase; quality?: CaptureQuality }> = ({ progress, phase, quality }) => {
    const r = CAPTURE_CONFIG.PROGRESS_RING_RADIUS;
    const stroke = CAPTURE_CONFIG.PROGRESS_RING_STROKE;
    const size = (r + stroke) * 2;
    const circumference = 2 * Math.PI * r;
    const offset = circumference * (1 - progress);

    let strokeColor = '#06b6d4'; // cyan
    if (phase === 'result') {
        if (quality === 'success') strokeColor = '#22c55e';
        else if (quality === 'warning') strokeColor = '#eab308';
        else strokeColor = '#ef4444';
    }

    return (
        <svg width={size} height={size} className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none">
            {/* Fondo del anillo */}
            <circle
                cx={r + stroke}
                cy={r + stroke}
                r={r}
                fill="none"
                stroke="rgba(255,255,255,0.1)"
                strokeWidth={stroke}
            />
            {/* Progreso */}
            <circle
                cx={r + stroke}
                cy={r + stroke}
                r={r}
                fill="none"
                stroke={strokeColor}
                strokeWidth={stroke}
                strokeDasharray={circumference}
                strokeDashoffset={offset}
                strokeLinecap="round"
                transform={`rotate(-90 ${r + stroke} ${r + stroke})`}
                className="transition-all duration-100"
            />
        </svg>
    );
};

// ─── Generacion de puntos ────────────────────────────────────────────────────

function generatePoints(
    patternType: '3_points' | '5_points' | '9_points'
): CalibrationPoint[] {
    const points: CalibrationPoint[] = [];

    points.push({ id: 'C', label: 'Centro', x: 0, y: 0, captured: false });

    if (patternType === '3_points') {
        points.push({ id: 'L', label: 'Izquierda', x: -1, y: 0, captured: false });
        points.push({ id: 'R', label: 'Derecha', x: 1, y: 0, captured: false });
    } else if (patternType === '5_points') {
        points.push({ id: 'L', label: 'Izquierda', x: -1, y: 0, captured: false });
        points.push({ id: 'R', label: 'Derecha', x: 1, y: 0, captured: false });
        points.push({ id: 'U', label: 'Arriba', x: 0, y: -1, captured: false });
        points.push({ id: 'D', label: 'Abajo', x: 0, y: 1, captured: false });
    } else if (patternType === '9_points') {
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

// ─── Componente principal ────────────────────────────────────────────────────

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
    const [lastEyeData, setLastEyeData] = useState<{
        left: { x: number; y: number } | null;
        right: { x: number; y: number } | null;
        timestamp: number;
    }>({ left: null, right: null, timestamp: 0 });

    // Estado de captura
    const [captureState, setCaptureState] = useState<CaptureState>({
        phase: 'idle',
        pointId: null,
        countdownValue: 0,
        samplingProgress: 0,
        result: null,
    });

    // Refs para captura
    const captureBufferRef = useRef<EyeSample[]>([]);
    const capturePhaseRef = useRef<CapturePhase>('idle');
    const captureTimersRef = useRef<{
        countdownInterval?: ReturnType<typeof setInterval>;
        samplingInterval?: ReturnType<typeof setInterval>;
        samplingTimeout?: ReturnType<typeof setTimeout>;
        resultTimeout?: ReturnType<typeof setTimeout>;
    }>({});

    // Video frame for ROI display
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const latestFrameRef = useRef<Blob | string | null>(null);

    // Ref para datos oculares (accesible desde callbacks sin deps)
    const lastEyeDataRef = useRef(lastEyeData);
    lastEyeDataRef.current = lastEyeData;

    const isCapturing = captureState.phase !== 'idle';

    // ─── Limpiar todos los timers ────────────────────────────────────────

    const clearAllCaptureTimers = useCallback(() => {
        const timers = captureTimersRef.current;
        if (timers.countdownInterval) clearInterval(timers.countdownInterval);
        if (timers.samplingInterval) clearInterval(timers.samplingInterval);
        if (timers.samplingTimeout) clearTimeout(timers.samplingTimeout);
        if (timers.resultTimeout) clearTimeout(timers.resultTimeout);
        captureTimersRef.current = {};
    }, []);

    // ─── Cancelar captura ────────────────────────────────────────────────

    const cancelCapture = useCallback(() => {
        clearAllCaptureTimers();
        capturePhaseRef.current = 'idle';
        captureBufferRef.current = [];
        setCaptureState({
            phase: 'idle',
            pointId: null,
            countdownValue: 0,
            samplingProgress: 0,
            result: null,
        });
    }, [clearAllCaptureTimers]);

    // ─── Finalizar captura para un punto ─────────────────────────────────

    const finalizeCaptureForPoint = useCallback((pointId: string) => {
        const samples = captureBufferRef.current;
        const result = analyzeCaptureSamples(samples);

        capturePhaseRef.current = 'result';
        setCaptureState(prev => ({
            ...prev,
            phase: 'result',
            samplingProgress: 1,
            result,
        }));

        // Actualizar punto si la captura fue exitosa o warning
        if (result.quality !== 'failed') {
            setPoints(prev => prev.map(p => {
                if (p.id === pointId) {
                    return {
                        ...p,
                        captured: true,
                        eyeDataRight: result.medianRight || undefined,
                        eyeDataLeft: result.medianLeft || undefined,
                        captureQuality: result.quality,
                        qualityScore: result.qualityScore,
                    };
                }
                return p;
            }));
        }

        // Mostrar resultado y volver a idle
        captureTimersRef.current.resultTimeout = setTimeout(() => {
            capturePhaseRef.current = 'idle';
            captureBufferRef.current = [];
            setCaptureState({
                phase: 'idle',
                pointId: null,
                countdownValue: 0,
                samplingProgress: 0,
                result: null,
            });
        }, CAPTURE_CONFIG.RESULT_DISPLAY_MS);
    }, []);

    // ─── Iniciar fase de muestreo ────────────────────────────────────────

    const beginSampling = useCallback((pointId: string) => {
        captureBufferRef.current = [];
        capturePhaseRef.current = 'sampling';
        setCaptureState(prev => ({
            ...prev,
            phase: 'sampling',
            samplingProgress: 0,
        }));

        const startTime = Date.now();

        // Recolectar muestras a ~30fps
        captureTimersRef.current.samplingInterval = setInterval(() => {
            if (capturePhaseRef.current !== 'sampling') return;

            const data = lastEyeDataRef.current;
            captureBufferRef.current.push({
                left: data.left,
                right: data.right,
                timestamp: data.timestamp,
            });

            const elapsed = Date.now() - startTime;
            const progress = Math.min(1, elapsed / CAPTURE_CONFIG.SAMPLING_DURATION_MS);
            setCaptureState(prev => ({ ...prev, samplingProgress: progress }));
        }, 33); // ~30fps

        // Finalizar tras duracion de muestreo
        captureTimersRef.current.samplingTimeout = setTimeout(() => {
            if (captureTimersRef.current.samplingInterval) {
                clearInterval(captureTimersRef.current.samplingInterval);
            }
            finalizeCaptureForPoint(pointId);
        }, CAPTURE_CONFIG.SAMPLING_DURATION_MS);
    }, [finalizeCaptureForPoint]);

    // ─── Iniciar captura completa ────────────────────────────────────────

    const startCapture = useCallback((pointId: string) => {
        if (isCapturing) return;

        clearAllCaptureTimers();
        captureBufferRef.current = [];
        capturePhaseRef.current = 'countdown';

        let countdown = CAPTURE_CONFIG.COUNTDOWN_SECONDS;

        setCaptureState({
            phase: 'countdown',
            pointId,
            countdownValue: countdown,
            samplingProgress: 0,
            result: null,
        });

        captureTimersRef.current.countdownInterval = setInterval(() => {
            countdown--;
            if (countdown <= 0) {
                if (captureTimersRef.current.countdownInterval) {
                    clearInterval(captureTimersRef.current.countdownInterval);
                }
                beginSampling(pointId);
            } else {
                setCaptureState(prev => ({
                    ...prev,
                    countdownValue: countdown,
                }));
            }
        }, CAPTURE_CONFIG.COUNTDOWN_INTERVAL_MS);
    }, [isCapturing, clearAllCaptureTimers, beginSampling]);

    // ─── Listener de eye_data ────────────────────────────────────────────

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

    // ─── Listener de video frames para ROI ───────────────────────────────

    useEffect(() => {
        const handleFrame = (data: Blob | string) => {
            latestFrameRef.current = data;
        };

        addListener('video_frame', handleFrame);

        let animationFrame: number;
        const renderROI = async () => {
            if (canvasRef.current && latestFrameRef.current) {
                const canvas = canvasRef.current;
                const ctx = canvas.getContext('2d');
                if (ctx) {
                    try {
                        if (latestFrameRef.current instanceof Blob) {
                            const bitmap = await createImageBitmap(latestFrameRef.current);
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

    // ─── Tecla ESC para cancelar captura ─────────────────────────────────

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                if (isCapturing) {
                    cancelCapture();
                } else {
                    onCancel();
                }
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isCapturing, cancelCapture, onCancel]);

    // ─── Cleanup al desmontar ────────────────────────────────────────────

    useEffect(() => {
        return () => clearAllCaptureTimers();
    }, [clearAllCaptureTimers]);

    // ─── Click en punto ──────────────────────────────────────────────────

    const handlePointClick = useCallback((pointId: string) => {
        if (isCapturing) return;
        startCapture(pointId);
    }, [isCapturing, startCapture]);

    // ─── Reset punto ─────────────────────────────────────────────────────

    const handleResetPoint = useCallback((pointId: string) => {
        if (isCapturing) return;
        setPoints(prev => prev.map(p => {
            if (p.id === pointId) {
                return { ...p, captured: false, eyeDataRight: undefined, eyeDataLeft: undefined, captureQuality: undefined, qualityScore: undefined };
            }
            return p;
        }));
    }, [isCapturing]);

    // ─── Reset todo ──────────────────────────────────────────────────────

    const handleResetAll = useCallback(() => {
        if (isCapturing) return;
        setPoints(generatePoints(patternType));
    }, [patternType, isCapturing]);

    // ─── Verificar completitud ───────────────────────────────────────────

    const allCaptured = points.every(p => p.captured);
    const capturedCount = points.filter(p => p.captured).length;

    // ─── Completar calibracion ───────────────────────────────────────────

    const handleComplete = useCallback(async () => {
        if (!allCaptured || isCapturing) return;

        const result: CalibrationResult = {
            points: points.map(p => ({
                id: p.id,
                angleX: p.x * horizontalAngle,
                angleY: -(p.y * verticalAngle),
                pixelRight: p.eyeDataRight || { x: 0, y: 0 },
                pixelLeft: p.eyeDataLeft || { x: 0, y: 0 }
            })),
            patientDistance,
            timestamp: Date.now()
        };

        await emit('manual_calibration_complete', result);
        onComplete(result);
    }, [allCaptured, isCapturing, points, horizontalAngle, verticalAngle, patientDistance, onComplete]);

    // ─── Posicion de punto en pantalla ───────────────────────────────────

    const getPointScreenPosition = (point: CalibrationPoint) => {
        const marginX = 15;
        const marginY = 15;
        const x = 50 + (point.x * (50 - marginX));
        const y = 50 + (point.y * (50 - marginY));
        return { x: `${x}%`, y: `${y}%` };
    };

    // ─── Color de calidad ────────────────────────────────────────────────

    const getQualityColor = (quality?: CaptureQuality) => {
        if (quality === 'success') return { bg: 'bg-green-500', border: 'border-green-500', text: 'text-green-400', hex: '#22c55e' };
        if (quality === 'warning') return { bg: 'bg-yellow-500', border: 'border-yellow-500', text: 'text-yellow-400', hex: '#eab308' };
        return { bg: 'bg-red-500', border: 'border-red-500', text: 'text-red-400', hex: '#ef4444' };
    };

    // ─── Render ──────────────────────────────────────────────────────────

    return (
        <div className="h-screen w-screen bg-black text-white relative overflow-hidden cursor-default">
            {/* Header */}
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 bg-black/80 backdrop-blur-sm border border-white/10 rounded-xl px-6 py-3 text-center">
                <h2 className="text-lg font-bold mb-1">Calibracion Manual VNG</h2>
                <p className="text-sm text-gray-400">
                    {isCapturing
                        ? captureState.phase === 'countdown'
                            ? 'Pida al paciente que mire fijamente al punto...'
                            : captureState.phase === 'sampling'
                                ? 'Capturando datos oculares...'
                                : 'Analizando captura...'
                        : 'Indique al paciente que mire cada punto. Haga clic en el punto cuando el paciente lo este mirando.'
                    }
                </p>
                <div className="mt-2 text-xs text-gray-500">
                    Patron: {patternType.replace('_', ' ')} | Angulos: {horizontalAngle}° H / {verticalAngle}° V | Distancia: {patientDistance}cm
                </div>
            </div>

            {/* Progreso */}
            <div className="absolute top-4 right-4 z-20 bg-black/80 backdrop-blur-sm border border-white/10 rounded-lg px-4 py-2">
                <div className="text-xs text-gray-400 mb-1">Progreso</div>
                <div className="text-lg font-bold">
                    <span className={capturedCount === points.length ? 'text-green-400' : 'text-white'}>
                        {capturedCount}
                    </span>
                    <span className="text-gray-500"> / {points.length}</span>
                </div>
            </div>

            {/* ROI Preview */}
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
                <div className="px-2 py-1 bg-black/50 text-[9px] font-mono flex gap-4">
                    <div className="text-red-400">
                        OD: {lastEyeData.right ? `(${lastEyeData.right.x.toFixed(1)}, ${lastEyeData.right.y.toFixed(1)})` : '--'}
                    </div>
                    <div className="text-cyan-400">
                        OI: {lastEyeData.left ? `(${lastEyeData.left.x.toFixed(1)}, ${lastEyeData.left.y.toFixed(1)})` : '--'}
                    </div>
                </div>
            </div>

            {/* Puntos de calibracion */}
            {points.map(point => {
                const pos = getPointScreenPosition(point);
                const isCaptureTarget = captureState.pointId === point.id;
                const showCountdown = isCaptureTarget && captureState.phase === 'countdown';
                const showSampling = isCaptureTarget && captureState.phase === 'sampling';
                const showResult = isCaptureTarget && captureState.phase === 'result';
                const qualityColors = point.captureQuality ? getQualityColor(point.captureQuality) : null;

                return (
                    <button
                        key={point.id}
                        onClick={() => handlePointClick(point.id)}
                        onContextMenu={(e) => {
                            e.preventDefault();
                            handleResetPoint(point.id);
                        }}
                        disabled={isCapturing && !isCaptureTarget}
                        style={{ left: pos.x, top: pos.y }}
                        className={`absolute -translate-x-1/2 -translate-y-1/2 group transition-all duration-200 ${
                            isCapturing && !isCaptureTarget ? 'opacity-30 cursor-not-allowed' : ''
                        } ${isCaptureTarget ? 'scale-110' : ''}`}
                    >
                        {/* Anillo de progreso SVG */}
                        {(showSampling || showResult) && (
                            <CaptureProgressRing
                                progress={captureState.samplingProgress}
                                phase={captureState.phase}
                                quality={captureState.result?.quality}
                            />
                        )}

                        {/* Circulo objetivo */}
                        <div className={`relative w-12 h-12 rounded-full border-2 flex items-center justify-center transition-all ${
                            showCountdown
                                ? 'bg-yellow-500/20 border-yellow-500 animate-pulse'
                                : showSampling
                                    ? 'bg-cyan-500/20 border-cyan-500'
                                    : showResult
                                        ? captureState.result?.quality === 'success'
                                            ? 'bg-green-500/30 border-green-500'
                                            : captureState.result?.quality === 'warning'
                                                ? 'bg-yellow-500/30 border-yellow-500'
                                                : 'bg-red-500/30 border-red-500'
                                        : point.captured
                                            ? qualityColors
                                                ? `${qualityColors.bg}/20 ${qualityColors.border}`
                                                : 'bg-green-500/20 border-green-500'
                                            : 'bg-red-500/20 border-red-500 hover:bg-red-500/40 hover:scale-110'
                        }`}>
                            {/* Countdown superpuesto */}
                            {showCountdown && (
                                <span className="text-xl font-black text-yellow-400 animate-pulse">
                                    {captureState.countdownValue}
                                </span>
                            )}

                            {/* Punto interno (solo si no hay countdown) */}
                            {!showCountdown && (
                                <div className={`w-3 h-3 rounded-full ${
                                    showSampling
                                        ? 'bg-cyan-400'
                                        : point.captured
                                            ? qualityColors ? qualityColors.bg : 'bg-green-500'
                                            : 'bg-red-500'
                                }`} />
                            )}

                            {/* Check si capturado */}
                            {point.captured && !isCaptureTarget && (
                                <div className={`absolute -top-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center ${
                                    qualityColors ? qualityColors.bg : 'bg-green-500'
                                }`}>
                                    <Check className="w-3 h-3 text-white" />
                                </div>
                            )}

                            {/* Badge de calidad si hay score */}
                            {point.captured && point.qualityScore !== undefined && !isCaptureTarget && (
                                <div className={`absolute -bottom-1 -right-1 px-1 rounded text-[8px] font-bold ${
                                    qualityColors ? `${qualityColors.bg} text-white` : 'bg-green-500 text-white'
                                }`}>
                                    {point.qualityScore}%
                                </div>
                            )}
                        </div>

                        {/* Resultado flash */}
                        {showResult && captureState.result && (
                            <div className={`absolute -bottom-6 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded text-[10px] font-bold whitespace-nowrap ${
                                captureState.result.quality === 'success'
                                    ? 'bg-green-500/80 text-white'
                                    : captureState.result.quality === 'warning'
                                        ? 'bg-yellow-500/80 text-white'
                                        : 'bg-red-500/80 text-white'
                            }`}>
                                {captureState.result.quality === 'success'
                                    ? `Excelente ${captureState.result.qualityScore}%`
                                    : captureState.result.quality === 'warning'
                                        ? `Aceptable ${captureState.result.qualityScore}% - Considere re-capturar`
                                        : 'Fallido - Sin datos suficientes'
                                }
                            </div>
                        )}

                        {/* Label */}
                        <div className={`absolute top-full left-1/2 -translate-x-1/2 mt-2 text-xs font-bold whitespace-nowrap ${
                            showCountdown || showSampling
                                ? 'text-cyan-400'
                                : point.captured
                                    ? qualityColors ? qualityColors.text : 'text-green-400'
                                    : 'text-gray-400'
                        }`}>
                            {point.label}
                        </div>

                        {/* Tooltip */}
                        {!isCapturing && (
                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                                <div className="bg-black/90 border border-white/20 rounded px-2 py-1 text-[10px] whitespace-nowrap">
                                    {point.captured ? 'Clic derecho para resetear' : 'Clic para capturar'}
                                </div>
                            </div>
                        )}
                    </button>
                );
            })}

            {/* Lineas de referencia */}
            <div className="absolute inset-0 pointer-events-none">
                <div className="absolute top-1/2 left-0 right-0 h-px bg-white/10" />
                <div className="absolute left-1/2 top-0 bottom-0 w-px bg-white/10" />
            </div>

            {/* Controles inferiores */}
            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex gap-3">
                <button
                    onClick={handleResetAll}
                    disabled={isCapturing}
                    className={`flex items-center gap-2 px-4 py-2 border rounded-lg transition-colors ${
                        isCapturing
                            ? 'bg-white/5 border-white/10 text-gray-600 cursor-not-allowed'
                            : 'bg-white/10 hover:bg-white/20 border-white/20'
                    }`}
                >
                    <RotateCcw className="w-4 h-4" />
                    Reiniciar Todo
                </button>

                <button
                    onClick={isCapturing ? cancelCapture : onCancel}
                    className="flex items-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-300 rounded-lg transition-colors"
                >
                    <X className="w-4 h-4" />
                    {isCapturing ? 'Cancelar Captura' : 'Cancelar'}
                </button>

                <button
                    onClick={handleComplete}
                    disabled={!allCaptured || isCapturing}
                    className={`flex items-center gap-2 px-6 py-2 rounded-lg font-bold transition-all ${
                        allCaptured && !isCapturing
                            ? 'bg-green-600 hover:bg-green-500 text-white shadow-lg shadow-green-900/30'
                            : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                    }`}
                >
                    <Check className="w-4 h-4" />
                    Completar Calibracion
                </button>
            </div>

            {/* Hint de atajos */}
            <div className="absolute bottom-4 right-4 text-[10px] text-gray-600">
                {isCapturing ? 'ESC para cancelar captura' : 'ESC para cancelar'}
            </div>
        </div>
    );
};
