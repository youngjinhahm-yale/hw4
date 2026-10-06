import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The FastAPI backend (backend/main.py) runs on port 8000.
const backend = process.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': backend,
      '/images': backend,
    },
  },
})
