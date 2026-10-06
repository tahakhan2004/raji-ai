import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev proxy forwards /api to the FastAPI backend.
// For a production build, set VITE_API_URL to the backend origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
});
