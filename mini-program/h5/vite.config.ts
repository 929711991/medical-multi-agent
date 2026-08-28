import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import site from '../service/site.json'

const consumerHost = site.dev.host.replace(/\/+$/, '')
const consumerOrigin = new URL(consumerHost).origin

export default defineConfig({
  root: fileURLToPath(new URL('./', import.meta.url)),
  server: {
    host: '127.0.0.1',
    port: 5174,
    strictPort: true,
    proxy: {
      '/api/v1/consumer': { target: consumerOrigin, changeOrigin: true },
    },
  },
  build: { outDir: fileURLToPath(new URL('./dist/', import.meta.url)), emptyOutDir: true },
})
