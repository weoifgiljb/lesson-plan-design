import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

import DataTable from './DataTable.vue'
import type { TableColumn } from './table-types'

const columns: TableColumn[] = [
  { key: 'title', label: '课题' },
  { key: 'status', label: '状态' },
]

const rows = [{ id: 1, title: '示例课题', status: 'passed' }]

function mountTable(props: Record<string, unknown> = {}): ReturnType<typeof mount> {
  return mount(DataTable, {
    props: { rows, columns, ...props },
    global: { plugins: [ElementPlus] },
  })
}

describe('DataTable', () => {
  it('passes rows and column definitions to the table', () => {
    const wrapper = mountTable()
    const table = wrapper.findComponent({ name: 'ElTable' })
    expect(table.props('data')).toHaveLength(1)
    const headers = wrapper
      .findAllComponents({ name: 'ElTableColumn' })
      .map((column) => column.props('label'))
    expect(headers).toEqual(['课题', '状态'])
  })

  it('shows the empty state when rows are empty', () => {
    const wrapper = mountTable({ rows: [], emptyText: '还没有教案' })
    expect(wrapper.text()).toContain('还没有教案')
  })

  it('shows error code and emits retry', async () => {
    const wrapper = mountTable({
      rows: [],
      state: 'error',
      error: { code: 'NOT_FOUND', message: '读取失败', traceId: 'trace-1' },
    })
    expect(wrapper.text()).toContain('NOT_FOUND')
    const button = wrapper.findAll('button').find((item) => item.text().includes('重试'))
    expect(button).toBeTruthy()
    await button?.trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })

  it('renders pagination when requested', () => {
    const wrapper = mountTable({ showPagination: true, total: 42, page: 1, pageSize: 10 })
    expect(wrapper.find('.el-pagination').exists()).toBe(true)
  })
})
