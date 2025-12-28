const plugin = require('tailwindcss/plugin')

module.exports = plugin(function ({ addUtilities }) {
	addUtilities({
		'.custom-scrollbar::-webkit-scrollbar': {
			width: '4px',
		},
		'.custom-scrollbar::-webkit-scrollbar-thumb': {
			'background-color': 'var(--scrollbar-thumb-color, #cfcfcf)',
			'border-radius': '20px',
		},
		'.custom-scrollbar::-webkit-scrollbar-thumb:hover': {
			'background-color': '#c6c6c6',
		},
	})
})
