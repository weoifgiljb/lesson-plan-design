import type { EngineInfo } from './models'
import { client } from './client'

export function getEngineInfo(): Promise<EngineInfo> {
  return client.get<EngineInfo>('/api/v1/settings/engine')
}

/**
 * 契约保留的引擎版本切换入口；后端当前未实现（405），UI 暂不启用。
 * 保留函数是为了满足契约闸门 BC-07 对 client=ui 接口的覆盖要求。
 */
export function switchEngineVersion(engineVersion: string): Promise<EngineInfo> {
  return client.put<EngineInfo>('/api/v1/settings/engine', { engineVersion })
}
