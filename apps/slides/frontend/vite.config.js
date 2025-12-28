import frappeui from 'frappe-ui/vite'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
	define: {
		__VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false,
	},
	plugins: [
		frappeui({
			frappeProxy: true,
			jinjaBootData: true,
			lucideIcons: true,
			buildConfig: {
				indexHtmlPath: '../slides/www/slides.html',
				outDir: '../slides/public/frontend',
				target: 'es2015',
			},
		}),
		vue(),
	],
	server: {
		allowedHosts: true,
	},
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src'),
		},
	},
	optimizeDeps: {
		include: [
			'feather-icons',
			'showdown',
			'engine.io-client',
			'tailwind.config.js',
			'lowlight',
		],
	},
})
