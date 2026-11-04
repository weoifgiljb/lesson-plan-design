import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.spec.ts'],
    globals: true,
    // Element Plus 挂载在慢盘/并行负载下可能超过 5s；20s 只用于防环境抖动，不放宽断言。
    testTimeout: 20000,
  },
})
