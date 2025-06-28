import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(), 
    tailwindcss()
  ],
  server: {
    // These settings are for when you run `npm run dev`
    host: '192.168.88.115', // Good for accessing on your LAN
    port: 5175,
    allowedHosts: ['192.168.88.115', 'yeet.trazen.org', 'localhost'],
    
    // --- THIS IS THE PROXY CONFIGURATION FOR DEVELOPMENT ---
    proxy: {
      // Any request from our React app that starts with '/api'
      // will be forwarded to the target below.
      '/api': {
        // This is the address of your Python/Docker backend
        // from the perspective of the Vite dev server.
        target: 'http://localhost:5001',
        
        // This is crucial. It changes the 'Origin' header of the request
        // to match the target, which helps avoid CORS issues.
        changeOrigin: true,
        
        // This removes the '/api' prefix from the path before sending it on.
        // e.g., a request to '/api/parse_hl7' becomes '/parse_hl7'
        // which is what your Flask app expects.
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    }
  },
})