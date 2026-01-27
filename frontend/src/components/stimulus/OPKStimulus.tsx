import React, { useEffect, useState, useRef } from 'react';
import { OPKConfig } from '../../types/vng';

interface Props {
    config: OPKConfig;
    degToPx: (deg: number) => number;
    onComplete: () => void;
}

export const OPKStimulus: React.FC<Props> = ({ config, degToPx }) => {
    const [offset, setOffset] = useState(0);
    const startTimeRef = useRef<number | null>(null);
    const requestRef = useRef<number | null>(null);

    // Calculate stripe width in pixels
    const stripeWidthPx = degToPx(config.stripe_width || 5);
    const patternSize = stripeWidthPx * 2; // One white, one black

    const isVertical = config.direction === 'up' || config.direction === 'down';
    const isReverse = config.direction === 'left' || config.direction === 'up';

    // Velocity in pixels per second
    const velocityPx = degToPx(config.velocity);

    const animate = (time: number) => {
        if (!startTimeRef.current) startTimeRef.current = time;
        const t = (time - startTimeRef.current) / 1000; // seconds

        // Calculate offset based on time and velocity
        let newOffset = velocityPx * t;

        // Apply direction
        if (isReverse) {
            newOffset = -newOffset;
        }

        // Wrap around to prevent huge numbers
        newOffset = newOffset % patternSize;

        setOffset(newOffset);
        requestRef.current = requestAnimationFrame(animate);
    };

    useEffect(() => {
        startTimeRef.current = null;
        requestRef.current = requestAnimationFrame(animate);
        return () => {
            if (requestRef.current) cancelAnimationFrame(requestRef.current);
        };
    }, [config]);

    // Background gradient
    const bgImage = config.pattern === 'checkerboard'
        ? `repeating-conic-gradient(#000 0% 25%, #fff 0% 50%)`
        : `repeating-linear-gradient(${isVertical ? '0deg' : '90deg'}, #000, #000 ${stripeWidthPx}px, #fff ${stripeWidthPx}px, #fff ${patternSize}px)`;

    const bgSize = config.pattern === 'checkerboard'
        ? `${patternSize}px ${patternSize}px`
        : isVertical
            ? `100% ${patternSize}px`
            : `${patternSize}px 100%`;

    const bgPosition = isVertical ? `0px ${offset}px` : `${offset}px 0px`;

    return (
        <div
            style={{
                width: '100%',
                height: '100%',
                backgroundImage: bgImage,
                backgroundSize: bgSize,
                backgroundPosition: bgPosition,
                backgroundRepeat: 'repeat',
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
