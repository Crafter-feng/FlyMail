import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, resolve } from 'path'

// 从项目根目录 VERSION 文件读取版本号
const __dirname = dirname(fileURLToPath(import.meta.url))
let appVersion = '0.0.0'
try {
  appVersion = readFileSync(resolve(__dirname, '../VERSION'), 'utf-8').trim()
} catch {}

export default defineConfig({
  plugins: [vue()],
  base: '/app/flymail/',
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(appVersion),
  },
  build: {
    outDir: '../dist/ui',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/app/flymail/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/app\/flymail/, ''),
      },
      '/app/flymail/ws': {
        target: 'ws://localhost:8080',
        ws: true,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/app\/flymail/, ''),
      },
    },
  },
})
