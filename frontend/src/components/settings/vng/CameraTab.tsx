import React, { useState, useEffect } from 'react';
import { Camera, RefreshCw } from 'lucide-react';
import { SettingsSection } from '../shared/SettingsSection';
import { SettingsField } from '../shared/SettingsField';
import { SettingsToggle } from '../shared/SettingsToggle';

interface CameraTabProps {
    config: any;
    updateConfig: (path: string, value: any) => void;
    apiUrl: string;
}

export const CameraTab: React.FC<CameraTabProps> = ({ config, updateConfig, apiUrl }) => {
    const [cameras, setCameras] = useState<any[]>([]);
    const [resolutions, setResolutions] = useState<string[]>([]);
    const [isLoadingCameras, setIsLoadingCameras] = useState(false);
    const [applyingResolution, setApplyingResolution] = useState(false);

    useEffect(() => {
        fetchCameras();
    }, []);

    useEffect(() => {
        if (config.vng.camera.camera_id !== undefined) {
            fetchResolutions(config.vng.camera.camera_id);
        }
    }, [config.vng.camera.camera_id]);

    const fetchCameras = async () => {
        setIsLoadingCameras(true);
        try {
            const res = await fetch(`${apiUrl}/video/cameras`);
            const data = await res.json();
            if (data.cameras) setCameras(data.cameras);
        } catch (e) {
            console.error("Error fetching cameras:", e);
        } finally {
            setIsLoadingCameras(false);
        }
    };

    const fetchResolutions = async (cameraId: number) => {
        try {
            const res = await fetch(`${apiUrl}/video/resolutions?camera_id=${cameraId}`);
            const data = await res.json();
            if (data.resolutions) setResolutions(data.resolutions);
        } catch (e) {
            console.error("Error fetching resolutions:", e);
        }
    };

    const handleResolutionSelect = async (resolutionStr: string) => {
        const match = resolutionStr.match(/(\d+)x(\d+)@(\d+)/);
        if (match) {
            const width = parseInt(match[1]);
            const height = parseInt(match[2]);
            const fps = parseInt(match[3]);

            updateConfig('vng.camera.resolution_width', width);
            updateConfig('vng.camera.resolution_height', height);
            updateConfig('vng.camera.fps', fps);

            setApplyingResolution(true);
            try {
                await fetch(`${apiUrl}/video/config`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ width, height, fps })
                });
            } catch (e) {
                console.error('Error applying resolution:', e);
            } finally {
                setApplyingResolution(false);
            }
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
                            onChange={e => updateConfig('vng.camera.camera_id', Number(e.target.value))}
                        >
                            {cameras.map((c: any) => (
                                <option key={c.id} value={c.id}>{c.name} ({c.path})</option>
                            ))}
                            {cameras.length === 0 && <option value={config.vng.camera.camera_id}>Cámara {config.vng.camera.camera_id}</option>}
                        </select>
                        <button 
                            className="btn btn-secondary p-2 h-9" 
                            onClick={fetchCameras}
                            disabled={isLoadingCameras}
                        >
                            <RefreshCw className={`w-4 h-4 ${isLoadingCameras ? 'animate-spin' : ''}`} />
                        </button>
                    </div>
                </SettingsField>

                <SettingsField 
                    label="Resolución y Velocidad"
                    description={applyingResolution ? "Aplicando cambios..." : `Resolución actual: ${currentRes}`}
                >
                    <select
                        className="select h-9 py-1 text-sm"
                        value={currentRes}
                        onChange={e => handleResolutionSelect(e.target.value)}
                        disabled={applyingResolution}
                    >
                        {resolutions.length === 0 && <option value={currentRes}>{currentRes}</option>}
                        {resolutions.map((res: string) => (
                            <option key={res} value={res}>{res}</option>
                        ))}
                    </select>
                </SettingsField>

                <div className="grid grid-cols-2 gap-4">
                    <SettingsField label="Exposición (Manual)" description="Ajuste para compensar luz ambiente.">
                        <input
                            type="number" className="input h-9 text-sm"
                            value={config.vng.camera.exposure}
                            onChange={e => updateConfig('vng.camera.exposure', Number(e.target.value))}
                        />
                    </SettingsField>
                    <SettingsField label="Contraste" description="Mejora la visibilidad de la pupila.">
                        <input
                            type="number" className="input h-9 text-sm"
                            value={config.vng.camera.contrast}
                            onChange={e => updateConfig('vng.camera.contrast', Number(e.target.value))}
                        />
                    </SettingsField>
                </div>
            </SettingsSection>

            <SettingsSection title="Orientación y Transformación">
                <div className="grid grid-cols-2 gap-3">
                    <SettingsField label="Espejo Horizontal" inline>
                        <SettingsToggle 
                            checked={config.vng.camera.flip_horizontal}
                            onChange={val => updateConfig('vng.camera.flip_horizontal', val)}
                        />
                    </SettingsField>
                    <SettingsField label="Invertir Vertical" inline>
                        <SettingsToggle 
                            checked={config.vng.camera.flip_vertical}
                            onChange={val => updateConfig('vng.camera.flip_vertical', val)}
                        />
                    </SettingsField>
                </div>
            </SettingsSection>
        </div>
    );
};
