import React, { useEffect, useState } from 'react';
import { GazeConfig, StimulusTargetConfig } from '../../types/vng';
import { Target } from './Target';

interface Props {
    config: GazeConfig;
    targetConfig: StimulusTargetConfig;
    degToPx: (deg: number) => number;
    onComplete: () => void;
}

export const GazeStimulus: React.FC<Props> = ({ config, targetConfig, degToPx, onComplete }) => {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [sequence, setSequence] = useState<number[]>([]);

    useEffect(() => {
        // Initialize sequence
        const indices = config.points.map((_, i) => i);
        if (config.randomize_order) {
            // Fisher-Yates shuffle
            for (let i = indices.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [indices[i], indices[j]] = [indices[j], indices[i]];
            }
        }
        setSequence(indices);
    }, [config]);

    useEffect(() => {
        if (sequence.length === 0) return;

        const pointIndex = sequence[currentIndex];
        const point = config.points[pointIndex];
        const duration = point.duration * 1000;

        const timer = setTimeout(() => {
            if (currentIndex < sequence.length - 1) {
                setCurrentIndex(prev => prev + 1);
            } else {
                onComplete();
            }
        }, duration);

        return () => clearTimeout(timer);
    }, [currentIndex, sequence, config, onComplete]);

    if (sequence.length === 0) return null;

    const point = config.points[sequence[currentIndex]];
    const xPx = degToPx(point.x);
    const yPx = degToPx(point.y);
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
