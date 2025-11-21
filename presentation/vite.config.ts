import { defineConfig } from 'vite'

export default defineConfig({
  base: '/bayesian-optimization-for-combustion/',
  optimizeDeps: {
    include: [
      'plotly.js-dist-min',
      'd3',
      'd3-shape'
    ]
  },
  build: {
    commonjsOptions: {
      transformMixedEsModules: true
    }
  }
})
