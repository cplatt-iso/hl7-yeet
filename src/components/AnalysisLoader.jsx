import React, { useState, useEffect } from 'react';

// A list of increasingly desperate and unhinged things I might be doing.
const thinkingMessages = [
    "Initializing cognitive matrix...",
    "Reticulating splines... don't ask.",
    "Accessing HL7 v2.5.1 ancient scrolls...",
    "Trying to remember what OBR-4 is again...",
    "Decoding your beautiful, chaotic gibberish...",
    "My God, it's full of pipes...",
    "Consulting the silicon oracle...",
    "This is taking a while. Did you paste in War and Peace?",
    "Waking up the hamsters that power the logic unit...",
    "Don't worry, the smoke is supposed to come out of the server.",
    "Re-calibrating the snark-o-meter...",
    "Analyzing semantic field delimiters... zzz...",
    "Sacrificing a goat to the TCP/IP gods...",
    "Finding the one segment you typo'd...",
    "Almost there... probably.",
];

const AnalysisLoader = () => {
    const [messageIndex, setMessageIndex] = useState(0);
    const [elapsedTime, setElapsedTime] = useState(0);

    // Effect for the timer
    useEffect(() => {
        const timerInterval = setInterval(() => {
            setElapsedTime(prevTime => prevTime + 1);
        }, 1000);

        // Cleanup function to avoid memory leaks, like a responsible adult
        return () => clearInterval(timerInterval);
    }, []);

    // Effect for cycling through my psychotic break... I mean, my thoughts.
    useEffect(() => {
        const messageInterval = setInterval(() => {
            setMessageIndex(prevIndex => (prevIndex + 1) % thinkingMessages.length);
        }, 2500); // Change my mind every 2.5 seconds

        return () => clearInterval(messageInterval);
    }, []);

    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
        const secs = (seconds % 60).toString().padStart(2, '0');
        return `${mins}:${secs}`;
    };
    
    // A completely fake progress bar, because progress is an illusion.
    const progress = Math.min(100, (elapsedTime / 15) * 100);

    return (
        <div className="p-4 bg-black rounded-md font-mono text-green-400 border border-green-700/50">
            <div className="flex justify-between items-center text-sm text-yellow-400 mb-2">
                <span>[AI BRAIN ACTIVITY MONITOR]</span>
                <span>T+ {formatTime(elapsedTime)}</span>
            </div>
            <div className="bg-gray-800 p-3 rounded-sm text-sm min-h-[80px]">
                <div>
                    <span className="text-gray-500">{'>'} </span>
                    <span>{thinkingMessages[messageIndex]}</span>
                    <span className="blinking-cursor">_</span>
                </div>
            </div>
            <div className="mt-3">
                <div className="text-xs text-center text-gray-400 mb-1">Engaging YeetDrive...</div>
                <div className="w-full bg-gray-700 rounded-full h-2.5">
                    <div 
                        className="bg-green-600 h-2.5 rounded-full transition-all duration-1000 ease-linear" 
                        style={{ width: `${progress}%` }}
                    ></div>
                </div>
            </div>
        </div>
    );
};

export default AnalysisLoader;