import React from 'react';
import { StimulusTargetConfig } from '../../types/vng';

interface TargetProps {
    config: StimulusTargetConfig;
    x: number; // pixels from center
    y: number; // pixels from center
    sizePx: number;
}

export const Target: React.FC<TargetProps> = ({ config, x, y, sizePx }) => {
    const style: React.CSSProperties = {
        position: 'absolute',
        left: '50%',
        top: '50%',
        width: sizePx,
        height: sizePx,
        transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`,
        backgroundColor: config.color,
        opacity: config.brightness / 100,
    };

    if (config.shape === 'circle') {
        style.borderRadius = '50%';
    } else if (config.shape === 'square') {
        style.borderRadius = '0%';
    } 
    // Add logic for images/sprites later if needed

    return <div style={style} />;
};
