<script setup lang="ts">
import { computed } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

const props = defineProps<{ markdown: string }>()

const html = computed(() => {
  const rendered = marked.parse(props.markdown, { async: false })
  return DOMPurify.sanitize(rendered as string, { USE_PROFILES: { html: true } })
})
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html -- rendered HTML is sanitized by DOMPurify -->
  <div class="markdown-body" v-html="html" />
</template>

<style scoped>
.markdown-body {
  color: var(--lpp-text);
  font-size: 14px;
  line-height: 1.75;
  overflow-wrap: anywhere;
}

.markdown-body :deep(h1) {
  margin: 0 0 10px;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.markdown-body :deep(h2) {
  margin: 24px 0 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--lpp-border);
  font-size: 18px;
  font-weight: 600;
}

.markdown-body :deep(h3) {
  margin: 16px 0 4px;
  font-size: 15px;
  font-weight: 600;
}

.markdown-body :deep(p) {
  margin: 0 0 10px;
}

.markdown-body :deep(blockquote) {
  margin: 0 0 14px;
  padding: 8px 12px;
  border-left: 3px solid var(--lpp-primary);
  background: var(--lpp-layer);
  color: var(--lpp-text-muted);
}

.markdown-body :deep(blockquote p) {
  margin: 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 6px 0 12px;
  padding-left: 22px;
}

.markdown-body :deep(li) {
  margin: 2px 0;
}

.markdown-body :deep(table) {
  width: 100%;
  margin: 8px 0 16px;
  border-collapse: collapse;
  font-size: 13px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 7px 9px;
  border: 1px solid var(--lpp-border);
  text-align: left;
  vertical-align: top;
}

.markdown-body :deep(th) {
  background: var(--lpp-layer);
  color: var(--lpp-text-muted);
  font-weight: 600;
  white-space: nowrap;
}

.markdown-body :deep(code) {
  padding: 1px 4px;
  border-radius: var(--lpp-radius-tag);
  background: var(--lpp-layer);
  font-family: var(--lpp-font-numeric);
  font-size: 12px;
}

.markdown-body :deep(pre) {
  padding: 12px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-control);
  background: var(--lpp-layer);
  overflow: auto;
}

.markdown-body :deep(pre code) {
  padding: 0;
  background: transparent;
}

.markdown-body :deep(a) {
  color: var(--lpp-primary);
}

@media (max-width: 767px) {
  .markdown-body :deep(table) {
    display: block;
    overflow-x: auto;
    white-space: nowrap;
  }
}
</style>
