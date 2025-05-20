import React, { useState, useEffect } from 'react';
import apiService from '../services/ApiService';
import { isPlatform } from '../utils/platform';

/**
 * A component to test network connectivity to the Calliope server
 */
const NetworkTest: React.FC = () => {
  const [testResults, setTestResults] = useState<string[]>([]);
  const [isVisible, setIsVisible] = useState(true);
  
  // Run network connectivity tests on mount
  useEffect(() => {
    const runTests = async () => {
      addLog('Starting network connectivity tests...');
      addLog(`Platform detection - Capacitor: ${isPlatform.capacitor()}, iOS: ${isPlatform.ios()}, Android: ${isPlatform.android()}`);
      addLog(`API Base URL: ${apiService.getAxiosInstance().defaults.baseURL}`);
      
      // Try a simple ping endpoint first
      try {
        addLog('Testing connectivity to server root...');
        // Added timeout to avoid hanging
        const response = await fetch('http://localhost:8008/', { 
          signal: AbortSignal.timeout(3000) 
        });
        addLog(`Server root fetch: ${response.status} ${response.statusText}`);
      } catch (error) {
        addLog(`Server root fetch failed: ${error instanceof Error ? error.message : String(error)}`);
      }
      
      // Try multiple common hostnames
      const testUrls = [
        'http://localhost:8008/docs',
        'http://127.0.0.1:8008/docs',
        'http://host.docker.internal:8008/docs'
      ];
      
      for (const url of testUrls) {
        try {
          addLog(`Testing ${url}...`);
          const response = await fetch(url, { 
            signal: AbortSignal.timeout(2000)
          });
          addLog(`${url}: ${response.status} ${response.statusText}`);
        } catch (error) {
          addLog(`${url} failed: ${error instanceof Error ? error.message : String(error)}`);
        }
      }
      
      // Test our API service
      try {
        addLog('Testing ApiService with strategies endpoint...');
        const response = await apiService.getAxiosInstance().get('/v1/config/strategy/', {
          params: { client_id: 'test-client' },
          timeout: 5000
        });
        addLog(`ApiService strategies test successful! Got ${Array.isArray(response.data) ? response.data.length : 'unknown'} strategies`);
      } catch (error) {
        addLog(`ApiService strategies test failed: ${error instanceof Error ? error.message : String(error)}`);
      }
      
      // Try with the connectivity endpoint to see if we get a simpler response
      try {
        addLog('Testing ApiService with connectivity endpoint...');
        const response = await apiService.getAxiosInstance().get('/v1/connectivity/no-auth/', {
          timeout: 5000
        });
        addLog(`Connectivity test successful! Server: ${response.data?.server?.hostname}`);
        addLog(`Your IP seen by server: ${response.data?.client?.ip}`);
      } catch (error) {
        addLog(`Connectivity test failed: ${error instanceof Error ? error.message : String(error)}`);
      }
      
      // Try with the API key endpoint to test auth
      try {
        addLog('Testing ApiService with authenticated endpoint...');
        const response = await apiService.getAxiosInstance().get('/v1/connectivity/', {
          timeout: 5000,
          params: { client_id: 'test-client' }
        });
        addLog(`Auth test successful! Server info: ${response.data?.server?.platform}`);
      } catch (error) {
        addLog(`Auth test failed: ${error instanceof Error ? error.message : String(error)}`);
      }
      
      addLog('Network tests completed');
    };
    
    runTests();
  }, []);
  
  const addLog = (message: string) => {
    setTestResults(prev => [...prev, message]);
  };
  
  if (!isVisible) return null;
  
  return (
    <div 
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        backgroundColor: 'rgba(0,0,0,0.8)',
        color: 'white',
        padding: '10px',
        fontFamily: 'monospace',
        fontSize: '12px',
        maxHeight: '50%',
        overflowY: 'auto'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
        <h3 style={{ margin: 0 }}>Network Connectivity Test</h3>
        <button 
          onClick={() => setIsVisible(false)}
          style={{
            backgroundColor: 'red',
            color: 'white',
            border: 'none',
            borderRadius: '3px',
            padding: '3px 8px'
          }}
        >
          Close
        </button>
      </div>
      
      <div>
        {testResults.map((result, index) => (
          <div key={index} style={{ marginBottom: '5px' }}>
            {result}
          </div>
        ))}
      </div>
    </div>
  );
};

export default NetworkTest;