import React from 'react';

const YeetLoader = () => {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-gray-800 bg-opacity-75 z-10 backdrop-blur-sm">
      <svg
        width="200"
        height="100"
        viewBox="0 0 200 100"
        xmlns="http://www.w3.org/2000/svg"
        className="animate-yeet-pulse"
      >
        <text
          x="50%"
          y="50%"
          dy=".35em"
          textAnchor="middle"
          className="text-6xl md:text-7xl font-black fill-indigo-400 stroke-indigo-600"
          strokeWidth="1"
        >
          YEET!
        </text>
      </svg>
    </div>
  );
};

export default YeetLoader;