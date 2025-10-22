import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';

export const useServerSentEvents = (runId) => {
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState('connecting');
  const [error, setError] = useState(null);
  const eventSourceRef = useRef(null);
  const statusRef = useRef('connecting');
  const { token } = useAuth();

  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  useEffect(() => {
    if (!runId || !token) {
      return;
    }

    // Clean up existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setStatus('connecting');
    setError(null);

    try {
      // Create EventSource with token as URL parameter (EventSource doesn't support headers)
      const url = `${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/api/sse/run/${runId}?token=${encodeURIComponent(token)}`;
      const eventSource = new EventSource(url);

      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('SSE: Connected to run stream');
        setStatus('connected');
        setError(null);
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          switch (data.type) {
            case 'connection':
              console.log('SSE:', data.message);
              break;
              
            case 'log_update':
              setLogs(prevLogs => {
                // Check if we already have this event
                const existingEvent = prevLogs.find(log => log.id === data.event.id);
                if (existingEvent) {
                  return prevLogs; // Don't add duplicates
                }
                
                // Add new event in sorted order
                const newLogs = [...prevLogs, data.event];
                return newLogs.sort((a, b) => a.step_order - b.step_order || a.iteration - b.iteration);
              });
              break;
              
            case 'status_update':
              setStatus(data.status.toLowerCase());
              if (data.status === 'COMPLETED' || data.status === 'ERROR') {
                console.log(`SSE: Run ${runId} ${data.status}`);
              }
              break;
              
            case 'heartbeat':
              // Keep connection alive
              break;
              
            case 'error':
              console.error('SSE Error:', data.message);
              setError(data.message);
              break;
              
            default:
              console.log('SSE: Unknown message type:', data.type);
          }
        } catch (e) {
          console.error('SSE: Failed to parse message:', e);
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE: Connection error:', error);
        setStatus('error');
        setError('Connection lost');
        
        // Close the current connection to prevent reconnection loops
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        
        // Only auto-reconnect if we were previously connected
        if (statusRef.current === 'connected') {
          setTimeout(() => {
            console.log('SSE: Attempting to reconnect...');
            setStatus('connecting');
            setError(null);
          }, 3000);
        }
      };

    } catch (e) {
      console.error('SSE: Failed to create connection:', e);
      setError('Failed to connect');
      setStatus('error');
    }

    // Cleanup function
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [runId, token]);

  const disconnect = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setStatus('disconnected');
    setLogs([]);
  };

  return {
    logs,
    status,
    error,
    disconnect,
    isConnected: status === 'connected'
  };
};
