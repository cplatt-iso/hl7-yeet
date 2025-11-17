// Helper utilities for rendering sparkline charts without external charting deps.

const isFiniteNumber = (value) => typeof value === 'number' && Number.isFinite(value);

export const prepareSparklineData = (input, options = {}) => {
    const { width = 160, height = 48, strokeWidth = 2 } = options;
    const values = Array.isArray(input) ? input.filter(isFiniteNumber) : [];

    if (values.length < 2) {
        return {
            values,
            points: '',
            lastPoint: null,
            bounds: { min: null, max: null },
            width,
            height,
            strokeWidth,
        };
    }

    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const horizontalStep = values.length > 1 ? (width - strokeWidth) / (values.length - 1) : 0;
    const verticalPadding = strokeWidth;

    const coordinates = values.map((value, index) => {
        const x = strokeWidth / 2 + index * horizontalStep;
        const y = height - verticalPadding - ((value - min) / range) * (height - verticalPadding * 2);
        return { x, y };
    });

    return {
        values,
        points: coordinates.map(({ x, y }) => `${x},${y}`).join(' '),
        lastPoint: coordinates.at(-1) ?? null,
        bounds: { min, max },
        width,
        height,
        strokeWidth,
    };
};

export default prepareSparklineData;
