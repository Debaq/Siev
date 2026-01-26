import React, { useEffect, useRef } from 'react';
import { OPKConfig } from '../../types/vng';

interface Props {
    config: OPKConfig;
    degToPx: (deg: number) => number;
    onComplete: () => void;
}

export const OPKStimulus: React.FC<Props> = ({ config, degToPx }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const offsetRef = useRef(0);
    const requestRef = useRef<number | null>(null);
    const lastTimeRef = useRef<number>(0);

    // Calculate stripe width in pixels
    const stripeWidthPx = degToPx(config.stripe_width || 5); 
    const patternSize = stripeWidthPx * 2; // One white, one black

    const isVertical = config.direction === 'up' || config.direction === 'down';

    const animate = (time: number) => {
        if (!lastTimeRef.current) lastTimeRef.current = time;
        const deltaTime = (time - lastTimeRef.current) / 1000; // seconds
        lastTimeRef.current = time;

        const velocityDeg = config.velocity;
        // Use linear approximation for velocity to avoid tangent distortion for large angles
        // degToPx(1) gives the pixel size of 1 degree at the center.
        const velocityPx = degToPx(1) * velocityDeg;
        
        // Update offset
        let delta = velocityPx * deltaTime;
        
        // Direction handling
        if (config.direction === 'left' || config.direction === 'up') {
            offsetRef.current -= delta;
        } else {
            offsetRef.current += delta;
        }

        // Wrap around
        offsetRef.current = offsetRef.current % patternSize;

        // Direct DOM update for performance
        if (containerRef.current) {
            const bgPos = isVertical 
                ? `0px ${offsetRef.current}px` 
                : `${offsetRef.current}px 0px`;
            containerRef.current.style.backgroundPosition = bgPos;
        }

        requestRef.current = requestAnimationFrame(animate);
    };

    useEffect(() => {
        requestRef.current = requestAnimationFrame(animate);

        return () => {
            if (requestRef.current) cancelAnimationFrame(requestRef.current);
        };
    }, [config]); 

    // Construct Background Style (Static parts)
    const bgImage = config.pattern === 'checkerboard' 
        ? `repeating-conic-gradient(#000 0% 25%, #fff 0% 50%)` 
        : `repeating-linear-gradient(${isVertical ? '0deg' : '90deg'}, #000, #000 ${stripeWidthPx}px, #fff ${stripeWidthPx}px, #fff ${patternSize}px)`;

    const bgSize = config.pattern === 'checkerboard'
        ? `${patternSize}px ${patternSize}px`
        : '100% 100%';

    return (
        <div 
            ref={containerRef}
            style={{
                width: '100%',
                height: '100%',
                backgroundImage: bgImage,
                backgroundSize: bgSize,
                backgroundPosition: '0px 0px', // Initial
                willChange: 'background-position',
                position: 'relative'
            }}
        >
            {/* Central Fixation Point */}
            {config.fixation_enabled && (
                <div 
                    style={{
                        position: 'absolute',
                        top: '50%',
                        left: '50%',
                        width: '20px',
                        height: '20px',
                        backgroundColor: 'red',
                        borderRadius: '50%',
                        transform: 'translate(-50%, -50%)',
                        zIndex: 10,
                        border: '2px solid white'
                    }}
                />
            )}
        </div>
    );
};
