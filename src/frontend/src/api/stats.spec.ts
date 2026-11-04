import { beforeEach, describe, expect, it, vi } from 'vitest'

import { downloadStatsCsv, getStatsSummary, listStatRecords, toStatsParams } from './stats'

const get = vi.fn()
const download = vi.fn()

vi.mock('./client', () => ({
  client: {
    get: (...args: unknown[]) => get(...args),
    download: (...args: unknown[]) => download(...args),
  },
}))

describe('toStatsParams', () => {
  it('去掉空值、trim 字符串，并把 className 映射成后端别名 class', () => {
    expect(
      toStatsParams({
        course: ' 信息技术 ',
        week: 2,
        className: '计算机2301',
        teacher: '',
        dateFrom: '2026-10-01',
        dateTo: '',
      }),
    ).toEqual({
      course: '信息技术',
      week: 2,
      class: '计算机2301',
      dateFrom: '2026-10-01',
    })
  })

  it('没有任何筛选时返回空参数', () => {
    expect(toStatsParams()).toEqual({})
    expect(toStatsParams({ course: '  ', className: '', teacher: '   ' })).toEqual({})
  })
})

describe('stats API 参数', () => {
  beforeEach(() => {
    get.mockReset()
    download.mockReset()
  })

  it('汇总请求带上同一组筛选参数', async () => {
    get.mockResolvedValue({ metrics: [], filters: {}, scope: 'own' })
    await getStatsSummary({ course: '信息技术', className: '计算机2301', week: 2 })
    expect(get).toHaveBeenCalledWith('/api/v1/stats/summary', {
      course: '信息技术',
      week: 2,
      class: '计算机2301',
    })
  })

  it('下钻请求在同一组筛选上追加分页', async () => {
    get.mockResolvedValue({ items: [], page: 1, pageSize: 20, total: 0 })
    await listStatRecords({ course: '信息技术', page: 2, pageSize: 50 })
    expect(get).toHaveBeenCalledWith('/api/v1/stats/records', {
      course: '信息技术',
      page: 2,
      pageSize: 50,
    })
  })

  it('CSV 导出不能忽略筛选', async () => {
    download.mockResolvedValue(new Blob())
    await downloadStatsCsv({ course: '信息技术', dateFrom: '2026-10-01', dateTo: '2026-10-31' })
    expect(download).toHaveBeenCalledWith('/api/v1/stats/export.csv', {
      course: '信息技术',
      dateFrom: '2026-10-01',
      dateTo: '2026-10-31',
    })
  })
})
