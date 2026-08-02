/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Origin the API lives on in production, e.g. "https://api.lifu.doslan.com".
   *  Empty in dev, where Vite proxies /api to the local backend same-origin. */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
