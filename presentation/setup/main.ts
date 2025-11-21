import { useBibliography } from 'slidev-theme-foamscience/composables/useBibliography'
import { watch } from 'vue'

export default ({ app, $slidev }: any) => {
  const { loadJsonFromUrl, allReferences } = useBibliography()

  // Construct URL with base path support
  const baseUrl = import.meta.env.BASE_URL || '/'
  const referencesUrl = `${baseUrl}references.json`.replace(/\/+/g, '/')

  console.log('🔧 Setup: Base URL is', baseUrl)

  // Helper function to prepend base URL to image paths
  const withBase = (path: string) => {
    if (!path || path.startsWith('http') || path.startsWith('data:')) return path
    return `${baseUrl}${path.replace(/^\//, '')}`.replace(/\/+/g, '/')
  }

  // Global mixin to intercept img src attributes
  app.mixin({
    beforeMount() {
      // Watch for frontmatter changes and update logo paths
      if (this.$slidev?.nav?.currentSlideRoute?.meta?.slide?.frontmatter) {
        const fm = this.$slidev.nav.currentSlideRoute.meta.slide.frontmatter
        if (fm.logoLight && fm.logoLight.startsWith('/')) {
          fm.logoLight = withBase(fm.logoLight)
        }
        if (fm.logoDark && fm.logoDark.startsWith('/')) {
          fm.logoDark = withBase(fm.logoDark)
        }
      }
    }
  })

  // Also add a directive for transforming src attributes
  app.directive('base-src', {
    mounted(el: HTMLImageElement, binding: any) {
      if (el.tagName === 'IMG' && binding.value) {
        el.src = withBase(binding.value)
      }
    },
    updated(el: HTMLImageElement, binding: any) {
      if (el.tagName === 'IMG' && binding.value) {
        el.src = withBase(binding.value)
      }
    }
  })

  // Watch for config changes and update logo paths
  if ($slidev?.configs) {
    watch(() => $slidev.configs.logoLight, (newVal) => {
      if (newVal && newVal.startsWith('/') && !newVal.startsWith(baseUrl)) {
        $slidev.configs.logoLight = withBase(newVal)
      }
    }, { immediate: true })

    watch(() => $slidev.configs.logoDark, (newVal) => {
      if (newVal && newVal.startsWith('/') && !newVal.startsWith(baseUrl)) {
        $slidev.configs.logoDark = withBase(newVal)
      }
    }, { immediate: true })
  }

  // Also provide the withBase function globally
  app.config.globalProperties.$withBase = withBase

  // Load bibliography on app initialization (before any slides render)
  loadJsonFromUrl(referencesUrl).then((success) => {
    if (success) {
      const ids = allReferences.value.map(ref => ref.key)
      console.log('📚 Loaded bibliography with IDs:', ids)
      console.log('📚 Total references:', allReferences.value.length)
      allReferences.value.forEach(ref => {
        console.log(`  - ${ref.key}: ${ref.entry.title}`)
      })
    } else {
      console.error('❌ Failed to load bibliography')
    }
  }).catch((err) => {
    console.error('❌ Failed to load bibliography:', err)
  })
}
