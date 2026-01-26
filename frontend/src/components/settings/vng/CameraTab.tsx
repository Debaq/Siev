import React, { useState, useEffect } from 'react';
import { RefreshCw } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsField } from '../shared/SettingsField';
import { SettingsToggle } from '../shared/SettingsToggle';
import { useWebSocket } from '../../../contexts/WebSocketContext';

interface CameraTabProps {
    config: any;
    updateConfig: (path: string, value: any) => void;
}

export const CameraTab: React.FC<CameraTabProps> = ({ config, updateConfig }) => {
    const { cameras, resolutions, resolutionsCameraId, send, pythonStatus } = useWebSocket();
    const [applyingResolution, setApplyingResolution] = useState(false);

    // Debug log
    console.log('[CameraTab] Render - resolutions:', resolutions, 'pythonStatus:', pythonStatus);

    // Fetch resolutions when camera changes or on initial load (only when Python is connected)
    useEffect(() => {
        const cameraId = config.vng?.camera?.camera_id;
        console.log('[CameraTab] useEffect - cameraId:', cameraId, 'pythonStatus:', pythonStatus, 'resolutionsCameraId:', resolutionsCameraId);
        if (pythonStatus && cameraId !== undefined && cameraId !== resolutionsCameraId) {
            console.log('[CameraTab] Requesting resolutions for camera:', cameraId);
            send({ type: 'list_resolutions', camera_id: cameraId });
        }
    }, [config.vng?.camera?.camera_id, resolutionsCameraId, pythonStatus, send]);

    const handleRefreshCameras = () => {
        send({ type: 'list_cameras' });
    };

    const handleCameraChange = (newCameraId: number) => {
        updateConfig('vng.camera.camera_id', newCameraId);
        // Request resolutions for the new camera
        send({ type: 'list_resolutions', camera_id: newCameraId });
    };

    const handleResolutionSelect = async (resolutionStr: string) => {
        const match = resolutionStr.match(/(\d+)x(\d+)@(\d+)/);
        if (match) {
            const width = parseInt(match[1]);
            const height = parseInt(match[2]);
            const fps = parseInt(match[3]);
            const camera_id = config.vng.camera.camera_id;

            updateConfig('vng.camera.resolution_width', width);
            updateConfig('vng.camera.resolution_height', height);
            updateConfig('vng.camera.fps', fps);

            setApplyingResolution(true);
            // Send config via WebSocket with camera_id
            send({
                type: 'set_config',
                key: 'camera_setup',
                value: { camera_id, width, height, fps }
            });

            setTimeout(() => setApplyingResolution(false), 500);
        }
    };

    const currentRes = `${config.vng.camera.resolution_width}x${config.vng.camera.resolution_height}@${config.vng.camera.fps}`;

    return (
        <div className="space-y-6 animate-fade-in">
            <SettingsSection 
                title="Captura de Video" 
                description="Configure el dispositivo de entrada y los parámetros de captura para la oculografía."
            >
                <SettingsField label="Dispositivo de Entrada">
                    <div className="flex gap-2">
                        <select
                            className="select flex-1 h-9 py-1 text-sm"
                            value={config.vng.camera.camera_id}
                            onChange={e => handleCameraChange(Number(e.target.value))}
                        >
                            {cameras.map((c: any) => (
                                <option key={c.id} value={c.id}>{c.name} ({c.path})</option>
                            ))}
                            {cameras.length === 0 && <option value={config.vng.camera.camera_id}>Cámara {config.vng.camera.camera_id}</option>}
                        </select>
                        <button
                            className="btn btn-secondary p-2 h-9"
                            onClick={handleRefreshCameras}
                            title="Refrescar lista de cámaras"
                        >
                            <RefreshCw className="w-4 h-4" />
                        </button>
                    </div>
                </SettingsField>

                <SettingsField
                    label="Resolución y Velocidad"
                    description={applyingResolution ? "Aplicando cambios..." : `Resolución actual: ${currentRes}`}
                >
                    <div className="flex gap-2">
                        <select
                            className="select flex-1 h-9 py-1 text-sm"
                            value={currentRes}
                            onChange={e => handleResolutionSelect(e.target.value)}
                            disabled={applyingResolution}
                        >
                            {resolutions.length > 0 ? (
                                resolutions.map((res: string) => (
                                    <option key={res} value={res}>{res}</option>
                                ))
                            ) : (
                                <option value={currentRes}>{currentRes}</option>
                            )}
                        </select>
                        <button
                            className="btn btn-secondary p-2 h-9"
                            onClick={() => send({ type: 'list_resolutions', camera_id: config.vng.camera.camera_id })}
                            title="Refrescar resoluciones"
                        >
                            <RefreshCw className="w-4 h-4" />
                        </button>
                    </div>
                </SettingsField>

                <div className="grid grid-cols-2 gap-4">
                    <SettingsField label="Exposición (Manual)" description="Ajuste para compensar luz ambiente.">
                        <input
                            type="number" className="input h-9 text-sm"
                            value={config.vng.camera.exposure}
                            onChange={e => {
                                const val = Number(e.target.value);
                                updateConfig('vng.camera.exposure', val);
                                send({ type: 'set_config', key: 'exposure', value: val });
                            }}
                        />
                    </SettingsField>
                    <SettingsField label="Contraste" description="Mejora la visibilidad de la pupila.">
                        <input
                            type="number" className="input h-9 text-sm"
                            value={config.vng.camera.contrast}
                            onChange={e => {
                                const val = Number(e.target.value);
                                updateConfig('vng.camera.contrast', val);
                                send({ type: 'set_config', key: 'contrast', value: val });
                            }}
                        />
                    </SettingsField>
                </div>
            </SettingsSection>

            <SettingsSection title="Orientación y Transformación">
                <div className="grid grid-cols-2 gap-3">
                    <SettingsField label="Espejo Horizontal" inline>
                        <SettingsToggle 
                            checked={config.vng.camera.flip_horizontal}
                            onChange={val => {
                                updateConfig('vng.camera.flip_horizontal', val);
                                send({ type: 'set_config', key: 'flip_h', value: val });
                            }}
                        />
                    </SettingsField>
                    <SettingsField label="Invertir Vertical" inline>
                        <SettingsToggle 
                            checked={config.vng.camera.flip_vertical}
                            onChange={val => {
                                updateConfig('vng.camera.flip_vertical', val);
                                send({ type: 'set_config', key: 'flip_v', value: val });
                            }}
                        />
                    </SettingsField>
                </div>
            </SettingsSection>
        </div>
    );
};