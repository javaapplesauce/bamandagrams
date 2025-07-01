// frontend/vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 3000,
    proxy: {
      // Proxy websocket and API calls to backend (for dev convenience)
      '/socket.io': {
        target: 'http://backend:8000',
        ws: true
      },
      '/auth': {
        target: 'http://backend:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  }
});
