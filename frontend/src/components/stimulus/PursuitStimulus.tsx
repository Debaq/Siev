import React, { useEffect, useState, useRef } from 'react';
import { PursuitConfig, StimulusTargetConfig } from '../../types/vng';
import { Target } from './Target';

interface Props {
    config: PursuitConfig;
    targetConfig: StimulusTargetConfig;
    degToPx: (deg: number) => number;
    onComplete: () => void;
}

export const PursuitStimulus: React.FC<Props> = ({ config, targetConfig, degToPx, onComplete }) => {
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const startTimeRef = useRef<number | null>(null);
    const requestRef = useRef<number | null>(null);

    const animate = (time: number) => {
        if (!startTimeRef.current) startTimeRef.current = time;
        const t = (time - startTimeRef.current) / 1000; // seconds

        let x = 0;
        let y = 0;

        // Calculate position based on type
        if (config.type === 'sinusoidal') {
            const freq = config.frequencies[0];
            const amp = config.amplitudes[0] || 20;
            // x(t) = A * sin(2 * pi * f * t)
            const val = amp * Math.sin(2 * Math.PI * freq * t);
            
            if (config.direction === 'horizontal') x = val;
            else y = val;

            // Check completion (cycles)
            if (t > config.cycles_per_frequency / freq) {
                onComplete();
                return;
            }

        } else if (config.type === 'sum_of_sines') {
            // Sum multiple sines
            let val = 0;
            config.frequencies.forEach((f, i) => {
                const amp = config.amplitudes[i] || (config.amplitudes[0] / (i + 1));
                val += amp * Math.sin(2 * Math.PI * f * t);
            });
            // Normalize amplitude sum? Maybe not needed if user inputs sensible values.

             if (config.direction === 'horizontal') x = val;
             else y = val;
             
             // Run for fixed time (e.g., 20s)
             if (t > 20) {
                 onComplete();
                 return;
             }

        } else if (config.type === 'step_ramp') {
             // Step-Ramp (Rashbass)
             // Step to side, ramp back
             const amp = config.amplitudes[0] || 10;
             const velocity = 20; // deg/s
             
             // Loop every few seconds
             const period = 2.0;
             const cycleT = t % period;
             
             if (cycleT < 0.1) {
                 // Center gap
                 x = 0;
             } else {
                 // Jump to +Amp
                 // Move at -Velocity
                 const runTime = cycleT - 0.1;
                 x = amp - (velocity * runTime);
             }
             
             if (config.direction === 'vertical') {
                 y = x; x = 0;
             }
             
             if (t > 10) { // Run for 10s
                 onComplete();
                 return;
             }
        }

        setPosition({ x, y });
        requestRef.current = requestAnimationFrame(animate);
    };

    useEffect(() => {
        requestRef.current = requestAnimationFrame(animate);
        return () => {
            if (requestRef.current) cancelAnimationFrame(requestRef.current);
        };
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
