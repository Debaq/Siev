import React, { useEffect, useState } from 'react';
import { CalibrationConfig, StimulusTargetConfig } from '../../types/vng';
import { Target } from './Target';

interface Props {
    config: CalibrationConfig;
    targetConfig: StimulusTargetConfig;
    degToPx: (deg: number) => number;
    screenResolution: { width: number; height: number };
    onComplete: () => void;
}

export const CalibrationStimulus: React.FC<Props> = ({ config, targetConfig, degToPx, onComplete }) => {
    const [currentIndex, setCurrentIndex] = useState(0);
    
    // Generate points based on config type
    // 5 points: Center, Left, Right, Up, Down
    // 9 points: + Corners
    const generatePoints = () => {
        const h = config.horizontal_fov;
        const v = config.vertical_fov;
        
        const center = { x: 0, y: 0 };
        
        if (config.type === 'points_3') {
            return [
                center,
                { x: -h, y: 0 },
                { x: h, y: 0 },
                center
            ];
        }
        
        if (config.type === 'points_5') {
            return [
                center,
                { x: -h, y: 0 },
                { x: h, y: 0 },
                { x: 0, y: -v },
                { x: 0, y: v },
                center
            ];
        }
        
        if (config.type === 'points_9') {
            return [
                center,
                { x: -h, y: -v }, { x: 0, y: -v }, { x: h, y: -v },
                { x: -h, y: 0 }, { x: 0, y: 0 }, { x: h, y: 0 },
                { x: -h, y: v }, { x: 0, y: v }, { x: h, y: v },
                center
            ];
        }

        // Fallback points_7 or other
        return [
            center,
            { x: -h, y: 0 }, { x: h, y: 0 },
            { x: 0, y: -v }, { x: 0, y: v },
            center
        ];
    };

    const points = generatePoints();

    useEffect(() => {
        // Use fixed duration for now (auto_advance assumed true or fallback)
        const duration = config.duration_per_point * 1000;
        
        const timer = setTimeout(() => {
            if (currentIndex < points.length - 1) {
                setCurrentIndex(prev => prev + 1);
            } else {
                onComplete();
            }
        }, duration);

        return () => clearTimeout(timer);
    }, [currentIndex, config.duration_per_point, points.length, onComplete]);

    const currentPoint = points[currentIndex];
    const xPx = degToPx(currentPoint.x);
    const yPx = degToPx(currentPoint.y);
    const sizePx = degToPx(targetConfig.size_degrees);

    return (
        <Target 
            config={targetConfig}
            x={xPx}
            y={yPx}
            sizePx={sizePx}
        />
    );
};
