import { describe, expect, it } from 'vitest'

import { filterCommands } from './command-types'
import type { CommandItem } from './command-types'

const commands: CommandItem[] = [
  { id: 'overview', title: '概览', group: '页面', keywords: 'overview 工作台', to: '/dashboard' },
  { id: 'styleguide', title: '设计验收', group: '页面', keywords: 'design 令牌', to: '/styleguide' },
  { id: 'logout', title: '退出登录', group: '操作' },
]

describe('filterCommands', () => {
  it('returns everything for an empty query', () => {
    expect(filterCommands(commands, '  ')).toHaveLength(3)
  })

  it('matches title, group and keywords', () => {
    expect(filterCommands(commands, '概览').map((item) => item.id)).toEqual(['overview'])
    expect(filterCommands(commands, '操作').map((item) => item.id)).toEqual(['logout'])
    expect(filterCommands(commands, 'design').map((item) => item.id)).toEqual(['styleguide'])
  })

  it('returns an empty list when nothing matches', () => {
    expect(filterCommands(commands, '不存在')).toEqual([])
  })
})
