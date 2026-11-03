import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import MarkdownView from './MarkdownView.vue'

const manual = `# 课堂教学教案

## 教学过程（共 1 课时）

| 教师活动 | 学生活动 |
|---|---|
| 播放视频：C 语言的产生和发展 | 记录易错点 |

## 板书、板画提纲

- 重点：C 语言的特点

<script>alert('x')</script>`

describe('MarkdownView', () => {
  it('renders manual-style headings and two-column teaching table', () => {
    const wrapper = mount(MarkdownView, { props: { markdown: manual } })
    expect(wrapper.find('h1').text()).toContain('课堂教学教案')
    expect(wrapper.findAll('h2')).toHaveLength(2)
    expect(wrapper.find('table').exists()).toBe(true)
    expect(wrapper.findAll('th')).toHaveLength(2)
    expect(wrapper.text()).toContain('C 语言的产生和发展')
    expect(wrapper.html()).not.toContain('<script>')
  })
})
