import { describe, expect, it, vi } from 'vitest'

import { usePagedQuery } from './usePagedQuery'

describe('usePagedQuery', () => {
  it('loads pages and updates total/page', async () => {
    const loader = vi.fn().mockResolvedValue({
      items: [{ id: 1 }],
      page: 1,
      pageSize: 10,
      total: 21,
    })
    const query = usePagedQuery(loader, 10)
    await query.load()
    expect(query.items.value).toEqual([{ id: 1 }])
    expect(query.total.value).toBe(21)
    expect(loader).toHaveBeenCalledWith(1, 10)
    await query.setPage(2)
    expect(loader).toHaveBeenLastCalledWith(2, 10)
  })

  it('resets to page 1 when page size changes', async () => {
    const loader = vi.fn().mockResolvedValue({ items: [], page: 1, pageSize: 20, total: 0 })
    const query = usePagedQuery(loader, 10)
    await query.setPage(3)
    await query.setPageSize(20)
    expect(loader).toHaveBeenLastCalledWith(1, 20)
  })
})
