/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

// Extend existing ImportMetaEnv interface
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  // more env variables...
}

// ImportMeta is already provided by vite/client
// No need to redeclare