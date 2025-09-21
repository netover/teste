import { resolve } from 'path';

export default {
  build: {
    // Output directory is relative to the project root.
    outDir: 'dist',
    emptyOutDir: true,

    // Generate a manifest file for the backend to read.
    manifest: true,

    rollupOptions: {
      // Define multiple entry points.
      input: {
        main: resolve(__dirname, 'static/js/main.ts'),
        config: resolve(__dirname, 'static/js/config.ts'),
        dashboard_editor: resolve(__dirname, 'static/js/dashboard_editor.ts'),
      },
    },
  },

  server: {
    // The port for the Vite development server.
    port: 5173,
    // Host on all interfaces to be accessible from inside the test container
    host: '0.0.0.0',
    // Enable CORS to allow the main backend to fetch scripts from this server.
    cors: true,
    // Proxy API requests to the Python backend running on port 63136.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:63136',
        changeOrigin: true,
        ws: true, // Also proxy websockets
      },
      '/ws': {
        target: 'ws://127.0.0.1:63136',
        ws: true,
      },
    },
  },
};
