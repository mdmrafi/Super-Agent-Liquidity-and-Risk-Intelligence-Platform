import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // envDir: BACKEND_PORT/FRONTEND_PORT live in the repo-root .env (shared
  // with backend/api/main.py), not a frontend-local one -- one source of
  // truth for the port both sides dial.
  const env = loadEnv(mode, '..', '')
  const backendPort = env.BACKEND_PORT || '8000'
  const frontendPort = Number(env.FRONTEND_PORT) || 5173

  return {
    plugins: [react()],
    envDir: '..',
    server: {
      port: frontendPort,
      proxy: {
        '/api': `http://localhost:${backendPort}`,
      },
    },
    define: {
      // Exposed to client code (App.jsx's connection-error hint) so the
      // displayed fix command always names the port actually configured,
      // not a hardcoded guess.
      'import.meta.env.VITE_BACKEND_PORT': JSON.stringify(backendPort),
    },
  }
})
