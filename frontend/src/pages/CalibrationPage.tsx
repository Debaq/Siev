import React, { useState } from 'react';
import { Ruler, Check, Monitor, Move, X, Maximize2, RefreshCcw, CheckCircle } from 'lucide-react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { emit } from '@tauri-apps/api/event';

// Pixels to draw the calibration box
const BOX_SIZE_PX = 500;
const VERIFICATION_DIST_MM = 100; // Distance to verify

type Step = 'positioning' | 'measuring' | 'success' | 'verification' | 'idle';

export const CalibrationPage: React.FC = () => {
    const [step, setStep] = useState<Step>('positioning');
    const [measuredWidthMm, setMeasuredWidthMm] = useState<number | ''>('');
    const [measuredHeightMm, setMeasuredHeightMm] = useState<number | ''>('');
    const [ppi, setPpi] = useState<number>(0);

    // Verification state
    const [verifyRealWidth, setVerifyRealWidth] = useState<string>('100');
    const [verifyRealHeight, setVerifyRealHeight] = useState<string>('100');

    const handleStart = async () => {
        console.log("Starting calibration sequence...");
        try {
            const win = getCurrentWindow();
            console.log("Window handle acquired, requesting fullscreen...");
            await win.setFullscreen(true);
            console.log("Fullscreen request sent.");
            setStep('measuring');
        } catch (e) {
            console.error("Failed to set fullscreen", e);
            // Proceed anyway for now so the UI doesn't get stuck
            setStep('measuring');
        }
    };

    const handleConfirm = async () => {
        if (!measuredWidthMm || measuredWidthMm <= 0 || !measuredHeightMm || measuredHeightMm <= 0) return;

        const widthInches = Number(measuredWidthMm) / 25.4;
        const calculatedPpi = BOX_SIZE_PX / widthInches;

        // Optional: Calculate Vertical PPI for logging/debugging
        const heightInches = Number(measuredHeightMm) / 25.4;
        const ppiY = BOX_SIZE_PX / heightInches;
        console.log(`Calibration: PPI_X=${calculatedPpi.toFixed(2)}, PPI_Y=${ppiY.toFixed(2)}`);

        setPpi(calculatedPpi);
        setStep('success');

        try {
            await emit('calibration_complete', {
                ppi: calculatedPpi,
                ppi_y: ppiY, // Send both just in case
                measured_width_mm: Number(measuredWidthMm),
                measured_height_mm: Number(measuredHeightMm),
                box_pixels: BOX_SIZE_PX
            });
        } catch (e) {
            console.error("Failed to emit calibration event", e);
        }
    };

    const goToVerification = () => {
        setVerifyRealWidth(VERIFICATION_DIST_MM.toString());
        setVerifyRealHeight(VERIFICATION_DIST_MM.toString());
        setStep('verification');
    };

    const handleAdjustAndFinish = async () => {
        const realX = parseFloat(verifyRealWidth);
        const realY = parseFloat(verifyRealHeight);

        if (!realX || !realY || realX <= 0 || realY <= 0) return;

        // Calculate corrected PPI based on verification measurements
        // factor = expected / actual
        const factorX = VERIFICATION_DIST_MM / realX;
        const factorY = VERIFICATION_DIST_MM / realY;

        const correctedPpiX = ppi * factorX;
        // Assume initial Y PPI was based on the same ppi (square pixels assumption from step 1 for drawing)
        // or better, if we had ppiY, we would use it. 
        // Since we didn't store ppiY in state (only in emit), let's approximate:
        const correctedPpiY = ppi * factorY; 

        console.log(`Adjusting Calibration. Factors: X=${factorX.toFixed(3)}, Y=${factorY.toFixed(3)}`);

        try {
            await emit('calibration_complete', {
                ppi: correctedPpiX,
                ppi_y: correctedPpiY,
                measured_width_mm: Number(measuredWidthMm), // Keep original ref
                measured_height_mm: Number(measuredHeightMm),
                box_pixels: BOX_SIZE_PX
            });
        } catch (e) {
            console.error("Failed to emit adjusted calibration", e);
        }

        setStep('idle');
    };

    const handleVerificationFail = () => {
        setMeasuredWidthMm('');
        setMeasuredHeightMm('');
        setStep('measuring');
    };

    const handleFinish = () => {
        setStep('idle');
    };

    const handleClose = async () => {
        await getCurrentWindow().close();
    };

    // --- STEP 1: Positioning (The "Cheat") ---
    if (step === 'positioning') {
        return (
            <div 
                data-tauri-drag-region
                className="h-screen w-screen bg-dark-950 text-white flex flex-col p-8 border-4 border-purple-500/30 relative select-none cursor-move"
            >
                {/* Close Button */}
                <button 
                    onClick={handleClose}
                    className="absolute top-2 right-2 p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors z-50 cursor-pointer"
                >
                    <X className="w-5 h-5" />
                </button>

                <div className="flex-1 flex flex-col items-center justify-center text-center gap-6 pointer-events-none">
                    <div className="p-6 bg-purple-500/10 rounded-full animate-pulse">
                        <Move className="w-12 h-12 text-purple-400" />
                    </div>
                    
                    <div className="max-w-md space-y-2">
                        <h1 className="text-2xl font-bold">Configuración de Pantalla</h1>
                        <p className="text-gray-400">
                            Arrastra esta ventana hacia el <strong>Monitor Externo</strong> donde se mostrarán los estímulos.
                        </p>
                    </div>

                    <div className="p-4 bg-dark-900 rounded-lg border border-dark-800 text-sm text-yellow-500/80 flex items-start gap-3 max-w-sm text-left">
                        <Monitor className="w-5 h-5 shrink-0 mt-0.5" />
                        <p>
                            Asegúrate de que la ventana esté completamente dentro de la pantalla secundaria antes de continuar.
                        </p>
                    </div>
                </div>

                <button 
                    onClick={handleStart}
                    className="w-full py-4 bg-purple-600 hover:bg-purple-500 text-white rounded-xl font-bold text-lg flex items-center justify-center gap-2 transition-all shadow-lg hover:shadow-purple-500/25 z-50 cursor-pointer"
                >
                    <Maximize2 className="w-5 h-5" />
                    COMENZAR CALIBRACIÓN
                </button>
            </div>
        );
    }

    // --- STEP 4: Idle / Logo Mode ---
    if (step === 'idle') {
        return (
            <div className="h-screen w-screen bg-black flex items-center justify-center cursor-none">
                {/* Logo centered */}
                <img 
                    src="/logo-large.png" 
                    alt="SIEV Logo" 
                    className="w-48 h-auto opacity-50 grayscale"
                />
                
                {/* Hidden close button in corner just in case */}
                <button 
                    onClick={handleClose}
                    className="absolute top-0 right-0 p-4 opacity-0 hover:opacity-100 text-dark-500 hover:text-red-500 transition-opacity"
                >
                    <X className="w-6 h-6" />
                </button>
            </div>
        );
    }

    // --- Verification Step ---
    if (step === 'verification') {
        // Calculate pixels for 100mm
        const verificationPixels = (VERIFICATION_DIST_MM / 25.4) * ppi;

        return (
            <div className="h-screen w-screen bg-black text-white flex flex-col items-center justify-center relative overflow-hidden">
                <div className="absolute top-8 text-center z-10 bg-black/50 p-4 rounded-xl backdrop-blur-sm border border-white/10 pointer-events-auto">
                    <h1 className="text-2xl font-bold flex items-center justify-center gap-2 mb-2">
                        <CheckCircle className="w-6 h-6 text-green-400" />
                        Verificación de Calibración
                    </h1>
                    <p className="text-gray-300 text-sm mb-4">
                        Mida la distancia entre los extremos rojos y corríjala si es necesario.
                    </p>
                    
                    <div className="grid grid-cols-2 gap-4 text-left">
                        <div>
                            <label className="block text-xs text-gray-400 mb-1">Horizontal (mm)</label>
                            <input 
                                type="number" 
                                value={verifyRealWidth}
                                onChange={(e) => setVerifyRealWidth(e.target.value)}
                                className="w-full bg-black/50 border border-white/20 rounded px-3 py-1 text-lg font-bold text-center focus:border-green-500 outline-none"
                            />
                        </div>
                        <div>
                            <label className="block text-xs text-gray-400 mb-1">Vertical (mm)</label>
                            <input 
                                type="number" 
                                value={verifyRealHeight}
                                onChange={(e) => setVerifyRealHeight(e.target.value)}
                                className="w-full bg-black/50 border border-white/20 rounded px-3 py-1 text-lg font-bold text-center focus:border-green-500 outline-none"
                            />
                        </div>
                    </div>
                </div>

                {/* Verification Markers Container - Centered */}
                <div className="relative flex items-center justify-center w-full h-full pointer-events-none">
                    
                    {/* Horizontal Axis */}
                    <div style={{ width: verificationPixels, height: 1 }} className="absolute bg-white/10 flex items-center justify-center">
                        {/* Left Marker */}
                        <div className="absolute left-0 w-px h-8 bg-red-500"></div>
                        {/* Right Marker */}
                        <div className="absolute right-0 w-px h-8 bg-red-500"></div>
                        
                        {/* Dashed Line */}
                        <div className="w-full border-t border-dashed border-red-500/50"></div>
                    </div>

                    {/* Vertical Axis */}
                    <div style={{ height: verificationPixels, width: 1 }} className="absolute bg-white/10 flex flex-col items-center justify-center">
                        {/* Top Marker */}
                        <div className="absolute top-0 h-px w-8 bg-red-500"></div>
                        {/* Bottom Marker */}
                        <div className="absolute bottom-0 h-px w-8 bg-red-500"></div>

                        {/* Dashed Line */}
                        <div className="h-full border-l border-dashed border-red-500/50"></div>
                    </div>

                    {/* Center Point */}
                    <div className="absolute w-2 h-2 bg-blue-500 rounded-full shadow-[0_0_10px_#3b82f6]"></div>
                </div>

                <div className="absolute bottom-12 flex flex-col items-center gap-4 bg-dark-900/80 p-6 rounded-2xl border border-white/10 backdrop-blur-md z-20">
                    <div className="flex gap-4 w-full">
                        <button 
                            onClick={handleVerificationFail}
                            className="flex-1 py-3 px-6 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/30 flex items-center justify-center gap-2 transition-colors whitespace-nowrap"
                        >
                            <RefreshCcw className="w-4 h-4" />
                            Reiniciar Todo
                        </button>
                        <button 
                            onClick={handleAdjustAndFinish}
                            className="flex-1 py-3 px-6 rounded-lg bg-green-600 hover:bg-green-500 text-white font-bold flex items-center justify-center gap-2 transition-colors shadow-lg shadow-green-900/20 whitespace-nowrap"
                        >
                            <Check className="w-4 h-4" />
                            Confirmar / Recalcular
                        </button>
                    </div>
                    <p className="text-xs text-gray-500">Si los valores son {VERIFICATION_DIST_MM}mm, la calibración es perfecta.</p>
                </div>
            </div>
        );
    }

    // --- STEP 2 & 3: Calibration & Success ---
    return (
        <div className="h-screen w-screen bg-black text-white flex flex-col items-center justify-center relative overflow-hidden">
            {step === 'measuring' && (
                <>
                    <div className="absolute top-8 text-center z-10 bg-black/50 p-4 rounded-xl backdrop-blur-sm border border-white/10">
                        <h1 className="text-2xl font-bold flex items-center justify-center gap-2 mb-2">
                            <Ruler className="w-6 h-6 text-purple-400" />
                            Calibración de Pantalla
                        </h1>
                        <p className="text-gray-300 max-w-md">
                            Mida el ancho y alto del cuadrado azul en milímetros.
                        </p>
                    </div>

                    {/* Calibration Box */}
                    <div 
                        style={{ width: BOX_SIZE_PX, height: BOX_SIZE_PX }}
                        className="border-4 border-blue-500 bg-blue-500/10 flex items-center justify-center relative shadow-[0_0_50px_rgba(59,130,246,0.5)]"
                    >
                        <div className="absolute -top-6 left-0 right-0 flex justify-center text-blue-400 text-xs font-mono">
                            {BOX_SIZE_PX} px
                        </div>
                        {/* Center Crosshair */}
                        <div className="w-4 h-px bg-white/50 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                        <div className="h-4 w-px bg-white/50 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                    </div>

                    <div className="absolute bottom-12 flex flex-col items-center gap-4 bg-dark-900/80 p-6 rounded-2xl border border-white/10 backdrop-blur-md">
                        <div className="flex gap-4">
                            <div className="flex flex-col items-center">
                                <label className="block text-xs text-gray-400 mb-1">Ancho (mm)</label>
                                <input 
                                    type="number" 
                                    value={measuredWidthMm}
                                    onChange={(e) => setMeasuredWidthMm(parseFloat(e.target.value))}
                                    className="bg-black/50 border border-white/20 rounded px-4 py-2 text-xl font-bold w-32 text-center focus:border-purple-500 outline-none"
                                    placeholder="0"
                                    autoFocus
                                />
                            </div>
                            <div className="flex flex-col items-center">
                                <label className="block text-xs text-gray-400 mb-1">Alto (mm)</label>
                                <input 
                                    type="number" 
                                    value={measuredHeightMm}
                                    onChange={(e) => setMeasuredHeightMm(parseFloat(e.target.value))}
                                    className="bg-black/50 border border-white/20 rounded px-4 py-2 text-xl font-bold w-32 text-center focus:border-purple-500 outline-none"
                                    placeholder="0"
                                />
                            </div>
                        </div>
                        
                        <div className="flex gap-3 w-full">
                            <button 
                                onClick={handleClose}
                                className="flex-1 py-2 px-4 rounded bg-white/10 hover:bg-white/20 text-gray-300 transition-colors"
                            >
                                Cancelar
                            </button>
                            <button 
                                onClick={handleConfirm}
                                disabled={!measuredWidthMm || !measuredHeightMm}
                                className="flex-1 py-2 px-4 rounded bg-purple-600 hover:bg-purple-500 text-white font-bold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                Confirmar
                            </button>
                        </div>
                    </div>
                </>
            )}

            {step === 'success' && (
                <div className="text-center p-8 bg-dark-900 border border-green-500/30 rounded-2xl max-w-md animate-in zoom-in duration-300">
                    <div className="w-16 h-16 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Check className="w-8 h-8" />
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-2">¡Calibración Exitosa!</h2>
                    <p className="text-gray-400 mb-6">
                        La densidad de píxeles calculada es de <strong className="text-white">{ppi.toFixed(2)} PPI</strong>.
                        La pantalla está lista para pruebas visuales.
                    </p>
                    <div className="flex flex-col gap-3">
                        <button 
                            onClick={goToVerification}
                            className="w-full py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-lg font-bold flex items-center justify-center gap-2"
                        >
                            <Ruler className="w-4 h-4" />
                            Verificar Calibración (Recomendado)
                        </button>
                        <button 
                            onClick={handleFinish}
                            className="w-full py-3 bg-transparent hover:bg-white/5 text-gray-400 hover:text-white rounded-lg font-medium border border-white/10"
                        >
                            Saltar y Finalizar
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};