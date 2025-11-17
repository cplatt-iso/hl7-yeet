import React from 'react';
import { prepareSparklineData } from '../utils/sparkline';

const Sparkline = ({ data, width = 160, height = 48, strokeWidth = 2, className = '' }) => {
    const prepared = prepareSparklineData(data, { width, height, strokeWidth });

    if (prepared.values.length < 2) {
        return (
            <div className={`flex h-full items-center justify-center text-xs text-gray-500 ${className}`}>
                Not enough data
            </div>
        );
    }

    const { points, lastPoint } = prepared;

    return (
        <svg
            width={width}
            height={height}
            viewBox={`0 0 ${width} ${height}`}
            className={`text-indigo-400 ${className}`}
            role="img"
            aria-label="sparkline"
        >
            <polyline
                fill="none"
                stroke="currentColor"
                strokeWidth={strokeWidth}
                strokeLinejoin="round"
                strokeLinecap="round"
                points={points}
            />
            {lastPoint && (
                <circle cx={lastPoint.x} cy={lastPoint.y} r={strokeWidth + 1} fill="currentColor" />
            )}
        </svg>
    );
};

export default Sparkline;
