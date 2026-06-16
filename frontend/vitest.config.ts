import { defineConfig } from 'vitest/config'

// Dedicated Vitest config (separate from vite.config.ts). esbuild's automatic JSX
// runtime lets component tests transform without the full React plugin; jsdom +
// the setup polyfill provide browser globals.
export default defineConfig({
  esbuild: { jsx: 'automatic', jsxImportSource: 'react' },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
    css: false,
  },
})
