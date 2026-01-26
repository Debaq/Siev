import React, { useEffect, useState, useRef } from 'react';
import { SaccadeConfig, StimulusTargetConfig } from '../../types/vng';
import { Target } from './Target';

interface Props {
    config: SaccadeConfig;
    targetConfig: StimulusTargetConfig;
    degToPx: (deg: number) => number;
    onComplete: () => void;
}

export const SaccadeStimulus: React.FC<Props> = ({ config, targetConfig, degToPx, onComplete }) => {
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const countRef = useRef(0);

    const getRandomInRange = (min: number, max: number) => {
        return Math.random() * (max - min) + min;
    };

    const getRandomSign = () => Math.random() < 0.5 ? -1 : 1;

    useEffect(() => {
        let timeoutId: NodeJS.Timeout;

        const runStep = () => {
            if (countRef.current >= config.count) {
                onComplete();
                return;
            }

            // Determine wait time (ISI)
            const isi = getRandomInRange(config.min_interval, config.max_interval) * 1000;

            // Determine next position
            let nextX = 0;
            let nextY = 0;

            if (config.type === 'random' || config.type === 'anti') {
                const amp = getRandomInRange(config.min_amplitude, config.max_amplitude);
                
                if (config.direction === 'horizontal') {
                    nextX = amp * getRandomSign();
                } else if (config.direction === 'vertical') {
                    nextY = amp * getRandomSign();
                } else {
                    // Both
                    if (Math.random() < 0.5) nextX = amp * getRandomSign();
                    else nextY = amp * getRandomSign();
                }
            } else if (config.type === 'fixed') {
                // Alternating left/right or up/down
                const amp = config.max_amplitude;
                const isEven = countRef.current % 2 === 0;
                const sign = isEven ? 1 : -1;
                
                if (config.direction === 'horizontal') nextX = amp * sign;
                else nextY = amp * sign;
            }

            // Sequence: Show at Center (optional?) or just jump?
            // "The Stimulus: A small point... Position: Random"
            // Usually Saccades jump FROM current pos TO new pos.
            // Or Center -> Target -> Center -> Target.
            // Let's implement: Jump to new pos.
            
            // Wait ISI then move
            timeoutId = setTimeout(() => {
                setPosition({ x: nextX, y: nextY });
                countRef.current += 1;
                runStep(); // Recursive call for next step
            }, isi);
        };

        // Start
        runStep();

        return () => clearTimeout(timeoutId);
    }, [config]);

    const xPx = degToPx(position.x);
    const yPx = degToPx(position.y);
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
