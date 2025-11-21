import { useBibliography } from 'slidev-theme-foamscience/composables/useBibliography'

export default () => {
  const { loadJsonFromUrl, allReferences } = useBibliography()

  // Construct URL with base path support
  const baseUrl = import.meta.env.BASE_URL || '/'
  const referencesUrl = `${baseUrl}references.json`.replace(/\/+/g, '/')

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
