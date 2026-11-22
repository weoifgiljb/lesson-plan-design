/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  /** 仅开发环境：登录页预填的开发账号。只放本地演示账号，勿填真实口令；写在 .env.local（已 gitignore） */
  readonly VITE_DEV_USERNAME?: string
  readonly VITE_DEV_PASSWORD?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
