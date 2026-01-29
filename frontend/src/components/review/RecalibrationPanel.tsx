import { useState } from 'react'
import { RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import type { CalibrationSnapshot } from '../../types/review'

interface RecalibrationPanelProps {
    calibration: CalibrationSnapshot | null
    loading: boolean
    onRecalibrate: (cal: CalibrationSnapshot) => void
}

export default function RecalibrationPanel({ calibration, loading, onRecalibrate }: RecalibrationPanelProps) {
    const [expanded, setExpanded] = useState(false)
    const [patientDistance, setPatientDistance] = useState(calibration?.patient_distance ?? 150)
    const [leftScaleX, setLeftScaleX] = useState(calibration?.left_scale[0] ?? 1)
    const [leftScaleY, setLeftScaleY] = useState(calibration?.left_scale[1] ?? 1)
    const [rightScaleX, setRightScaleX] = useState(calibration?.right_scale[0] ?? 1)
    const [rightScaleY, setRightScaleY] = useState(calibration?.right_scale[1] ?? 1)
    const [leftCenterX, setLeftCenterX] = useState(calibration?.left_center[0] ?? 0)
    const [leftCenterY, setLeftCenterY] = useState(calibration?.left_center[1] ?? 0)
    const [rightCenterX, setRightCenterX] = useState(calibration?.right_center[0] ?? 0)
    const [rightCenterY, setRightCenterY] = useState(calibration?.right_center[1] ?? 0)

    const handleRecalibrate = () => {
        if (!calibration) return
        const newCal: CalibrationSnapshot = {
            ...calibration,
            patient_distance: patientDistance,
            left_scale: [leftScaleX, leftScaleY],
            right_scale: [rightScaleX, rightScaleY],
            left_center: [leftCenterX, leftCenterY],
            right_center: [rightCenterX, rightCenterY],
            timestamp: new Date().toISOString(),
        }
        onRecalibrate(newCal)
    }

    if (!calibration) {
        return (
            <div className="bg-dark-900/50 border border-dark-800 rounded-lg p-3">
                <span className="text-xs text-dark-500">Sin datos de calibracion</span>
            </div>
        )
    }

    return (
        <div className="bg-dark-900/50 border border-dark-800 rounded-lg overflow-hidden">
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full px-3 py-2 flex items-center justify-between hover:bg-dark-800/50 transition-colors"
            >
                <span className="text-xs font-semibold text-dark-300">Recalibracion</span>
                {expanded ? <ChevronUp className="w-3.5 h-3.5 text-dark-500" /> : <ChevronDown className="w-3.5 h-3.5 text-dark-500" />}
            </button>

            {expanded && (
                <div className="px-3 pb-3 pt-1 border-t border-dark-800 space-y-3">
                    {/* Distance */}
                    <div>
                        <label className="text-[10px] text-dark-500 block mb-1">Distancia Paciente (cm)</label>
                        <input
                            type="range"
                            min={50}
                            max={300}
                            step={5}
                            value={patientDistance}
                            onChange={e => setPatientDistance(Number(e.target.value))}
                            className="w-full accent-siev-500"
                        />
                        <span className="text-[10px] text-dark-400">{patientDistance} cm</span>
                    </div>

                    {/* Scale factors */}
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <label className="text-[10px] text-dark-500 block mb-0.5">OD Escala X (°/px)</label>
                            <input
                                type="number"
                                step={0.0001}
                                value={rightScaleX}
                                onChange={e => setRightScaleX(Number(e.target.value))}
                                className="w-full bg-dark-800 border border-dark-700 rounded px-2 py-1 text-xs text-dark-200 focus:border-siev-500 outline-none"
                            />
                        </div>
                        <div>
                            <label className="text-[10px] text-dark-500 block mb-0.5">OD Escala Y (°/px)</label>
                            <input
                                type="number"
                                step={0.0001}
                                value={rightScaleY}
                                onChange={e => setRightScaleY(Number(e.target.value))}
                                className="w-full bg-dark-800 border border-dark-700 rounded px-2 py-1 text-xs text-dark-200 focus:border-siev-500 outline-none"
                            />
                        </div>
                        <div>
                            <label className="text-[10px] text-dark-500 block mb-0.5">OI Escala X (°/px)</label>
                            <input
                                type="number"
                                step={0.0001}
                                value={leftScaleX}
                                onChange={e => setLeftScaleX(Number(e.target.value))}
                                className="w-full bg-dark-800 border border-dark-700 rounded px-2 py-1 text-xs text-dark-200 focus:border-siev-500 outline-none"
                            />
                        </div>
                        <div>
                            <label className="text-[10px] text-dark-500 block mb-0.5">OI Escala Y (°/px)</label>
                            <input
                                type="number"
                                step={0.0001}
                                value={leftScaleY}
                                onChange={e => setLeftScaleY(Number(e.target.value))}
                                className="w-full bg-dark-800 border border-dark-700 rounded px-2 py-1 text-xs text-dark-200 focus:border-siev-500 outline-none"
                            />
                        </div>
                    </div>

                    {/* Center offsets */}
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <label className="text-[10px] text-dark-500 block mb-0.5">OD Centro X</label>
                            <input
                                type="number"
                                step={0.1}
                                value={rightCenterX}
                                onChange={e => setRightCenterX(Number(e.target.value))}
                                className="w-full bg-dark-800 border border-dark-700 rounded px-2 py-1 text-xs text-dark-200 focus:border-siev-500 outline-none"
                            />
                        </div>
                        <div>
                            <label className="text-[10px] text-dark-500 block mb-0.5">OD Centro Y</label>
                            <input
                                type="number"
                                step={0.1}
                                value={rightCenterY}
                                onChange={e => setRightCenterY(Number(e.target.value))}
                                className="w-full bg-dark-800 border border-dark-700 rounded px-2 py-1 text-xs text-dark-200 focus:border-siev-500 outline-none"
                            />
                        </div>
                        <div>
                            <label className="text-[10px] text-dark-500 block mb-0.5">OI Centro X</label>
                            <input
                                type="number"
                                step={0.1}
                                value={leftCenterX}
                                onChange={e => setLeftCenterX(Number(e.target.value))}
                                className="w-full bg-dark-800 border border-dark-700 rounded px-2 py-1 text-xs text-dark-200 focus:border-siev-500 outline-none"
                            />
                        </div>
                        <div>
                            <label className="text-[10px] text-dark-500 block mb-0.5">OI Centro Y</label>
                            <input
                                type="number"
                                step={0.1}
                                value={leftCenterY}
                                onChange={e => setLeftCenterY(Number(e.target.value))}
                                className="w-full bg-dark-800 border border-dark-700 rounded px-2 py-1 text-xs text-dark-200 focus:border-siev-500 outline-none"
                            />
                        </div>
                    </div>

                    <button
                        onClick={handleRecalibrate}
                        disabled={loading}
                        className="w-full btn btn-primary text-xs py-2 flex items-center justify-center gap-2"
                    >
                        <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                        {loading ? 'Recalculando...' : 'Recalcular Metricas'}
                    </button>
                </div>
            )}
        </div>
    )
}
