/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  /** 仅开发环境：登录页预填的开发账号，避免源码写死与种子数据漂移 */
  readonly VITE_DEV_USERNAME?: string
  readonly VITE_DEV_PASSWORD?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
