import { defineConfig } from 'wxt';
import tailwindcss from '@tailwindcss/vite';

// See https://wxt.dev/api/config.html
export default defineConfig({
  modules: ['@wxt-dev/module-react'],
  // Add permissions to query the active tab and execute content scripts programmatically
  manifest: {
    permissions: ["activeTab", "scripting"],
    host_permissions: ["<all_urls>"],
  },
  vite: () => ({
    plugins: [tailwindcss()],
  }),
});
