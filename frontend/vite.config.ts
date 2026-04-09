import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendTarget = env.VITE_BACKEND_TARGET || 'http://127.0.0.1:8000';

  return {
    base: '/',
    plugins: [vue()],

    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },

    server: {
      host: '0.0.0.0',
      port: 5173,
      strictPort: true,
      // Dev only: production traffic is handled by Nginx.
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          // /api/v1/projects -> /v1/projects
          rewrite: (path) => path.replace(/^\/api/, '')
        }
      }
    },

    build: {
      target: 'esnext',
      minify: 'esbuild',
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules')) {
              if (id.includes('mapbox-gl')) {
                return 'mapbox-vendor';
              }
              if (id.includes('echarts') || id.includes('zrender')) {
                return 'echarts-vendor';
              }
              if (id.includes('vue') || id.includes('pinia') || id.includes('vue-router')) {
                return 'vue-vendor';
              }
              return 'vendor';
            }
          }
        }
      }
    }
  };
});
