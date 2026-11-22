/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  /** 登录页预填的开发用户名，仅在 import.meta.env.DEV 下使用；值会被构建期内联，禁止放口令。
   *  配置见 src/frontend/.env.example，本地复制为 .env.development.local（.env* 已 gitignore） */
  readonly VITE_DEV_USERNAME?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
