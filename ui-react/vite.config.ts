import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Served by FastAPI under /v2 in "deployed" mode; in dev the API calls are
// proxied to the backend on 8081 so both UIs (vanilla and React) share the
// same data side-by-side.
export default defineConfig({
  plugins: [react()],
  base: '/v2/',
  server: {
    proxy: {
      '/llm-review': 'http://localhost:8081',
      '/docs': 'http://localhost:8081',
      '/openapi.json': 'http://localhost:8081',
    },
  },
})
