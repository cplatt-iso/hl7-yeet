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
  },
})