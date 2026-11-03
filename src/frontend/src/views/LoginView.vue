<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'

import BrandMark from '@/components/BrandMark.vue'
import { RequestError } from '@/api/client-error'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const isDev = import.meta.env.DEV

const formRef = ref<FormInstance>()
const usernameRef = ref<{ focus: () => void } | null>(null)
const form = reactive({
  username: isDev ? 'teacher01' : '',
  password: isDev ? 'Lesson2026' : '',
})
const loading = ref(false)
const errorMessage = ref('')
const errorTrace = ref('')

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function submit(): Promise<void> {
  if (!formRef.value) return
  errorMessage.value = ''
  errorTrace.value = ''
  formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await session.signIn(form.username, form.password)
      const redirect =
        typeof route.query.redirect === 'string' && route.query.redirect !== '/login'
          ? route.query.redirect
          : '/dashboard'
      await router.push(redirect)
    } catch (caught) {
      if (caught instanceof RequestError) {
        errorMessage.value = caught.message
        errorTrace.value = caught.traceId
      } else {
        errorMessage.value = '登录失败，请检查网络或稍后重试。'
      }
    } finally {
      loading.value = false
    }
  })
}

onMounted(() => {
  usernameRef.value?.focus()
})
</script>

<template>
  <main class="auth">
    <section class="auth-story" aria-label="平台简介">
      <div class="story-top">
        <BrandMark inverse :size="30" caption="平台端 v1.1" />
      </div>

      <div class="story-body">
        <h1>让每一份教案，<br />经得起对照。</h1>
        <p class="story-lead">
          三维目标、八步流程与证据链，落在同一个工作台上。写完、审完、导出，不用换工具。
        </p>

        <ul class="story-rules">
          <li>
            <strong>结构可校验</strong>
            <span>校标字段、八步流程与分钟合计，导入即校验。</span>
          </li>
          <li>
            <strong>证据可追溯</strong>
            <span>哈希、轮次、放行记录与审查状态，五项逐条对照。</span>
          </li>
          <li>
            <strong>版本可回滚</strong>
            <span>每次修订留下版本链与差异，导出的 DOCX 带哈希。</span>
          </li>
        </ul>
      </div>

      <svg class="story-art" viewBox="0 0 460 300" fill="none" aria-hidden="true">
        <g stroke="currentColor" stroke-width="1">
          <path d="M70 160l200-62 150 52-200 62z" />
          <path d="M70 108l200-62 150 52-200 62z" />
          <path d="M70 56l200-62 150 52-200 62z" opacity="0.6" />
          <path d="M70 56v104M270-6v104M420 46v104M220 112v104" opacity="0.5" />
          <path d="M116 146v48M154 132v48M192 119v48M230 106v48M268 93v48M306 80v48M344 67v48M382 54v48" opacity="0.7" />
        </g>
      </svg>

      <div class="story-foot">
        <span>东莞经贸学校 / 计算机教研组</span>
        <span class="mono">LPP / v1.1.0</span>
      </div>
    </section>

    <section class="auth-form" aria-label="登录">
      <div class="form-inner">
        <div class="form-head">
          <h2>登录</h2>
          <p class="form-lead">使用学校账号进入工作台。</p>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          :aria-describedby="errorMessage ? 'login-error' : undefined"
          @submit.prevent="submit"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              ref="usernameRef"
              v-model="form.username"
              autocomplete="username"
              placeholder="请输入用户名"
            />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              show-password
              autocomplete="current-password"
              placeholder="请输入密码"
            />
          </el-form-item>

          <el-alert
            v-if="errorMessage"
            id="login-error"
            class="login-error"
            type="error"
            :closable="false"
            show-icon
            :title="errorMessage"
            :description="errorTrace ? `traceId: ${errorTrace}` : ''"
          />

          <el-button class="login-submit" type="primary" native-type="submit" :loading="loading">
            登录
          </el-button>
        </el-form>

        <p class="register-link">
          还没有账号？<router-link to="/register">注册教师账号</router-link>
        </p>
        <el-alert
          v-if="route.query.registered || route.query.changed"
          class="form-notice"
          type="success"
          :closable="false"
          show-icon
          :title="route.query.changed ? '口令已更新，请用新口令登录。' : '注册成功，请用新账号登录并设置新口令。'"
        />
        <p v-if="isDev" class="demo-hint">
          本地开发：<code>teacher01</code> / <code>Lesson2026</code>
        </p>
        <p v-if="isDev" class="demo-link">
          <router-link to="/styleguide">查看设计验收</router-link>
        </p>
      </div>

      <p class="form-foot">遇到登录问题，请联系教研组长重置账号。</p>
    </section>
  </main>
</template>

<style scoped>
.auth {
  display: grid;
  grid-template-columns: minmax(0, 46%) minmax(0, 54%);
  min-height: 100vh;
  background: var(--lpp-surface);
}

.auth-story {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 32px;
  padding: 36px 44px;
  overflow: hidden;
  background:
    linear-gradient(rgba(240, 244, 239, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240, 244, 239, 0.035) 1px, transparent 1px),
    var(--lpp-nameplate);
  background-size: 32px 32px;
  color: var(--lpp-nameplate-text);
}

.story-top {
  position: relative;
  z-index: 1;
}

.story-body {
  position: relative;
  z-index: 1;
  max-width: 520px;
  margin-top: 24px;
}

.story-body h1 {
  color: var(--lpp-nameplate-text);
  font-size: clamp(30px, 3.4vw, 46px);
  font-weight: 600;
  line-height: 1.22;
  letter-spacing: -0.03em;
}

.story-lead {
  max-width: 40ch;
  margin-top: 16px;
  color: var(--lpp-nameplate-muted);
  font-size: var(--lpp-font-base);
  line-height: 1.75;
}

.story-rules {
  display: flex;
  flex-direction: column;
  margin: 32px 0 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid rgba(240, 244, 239, 0.14);
}

.story-rules li {
  display: grid;
  grid-template-columns: 108px minmax(0, 1fr);
  gap: 14px;
  padding: 11px 0;
  border-bottom: 1px solid rgba(240, 244, 239, 0.14);
}

.story-rules strong {
  color: var(--lpp-nameplate-text);
  font-size: var(--lpp-font-xs);
  font-weight: 600;
}

.story-rules span {
  color: var(--lpp-nameplate-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.55;
}

.story-art {
  position: absolute;
  right: -60px;
  bottom: 44px;
  width: 62%;
  max-width: 520px;
  color: var(--lpp-nameplate-text);
  opacity: 0.12;
  pointer-events: none;
}

.story-foot {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
  margin-top: auto;
  color: var(--lpp-nameplate-muted);
  font-size: 12px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 40px 48px;
  border-left: 1px solid var(--lpp-border);
  background: var(--lpp-surface);
}

.form-inner {
  width: min(360px, 100%);
  margin: 0 auto;
}

.form-head {
  margin-bottom: 24px;
}

.form-head h2 {
  font-size: var(--lpp-font-xl);
  font-weight: 600;
  letter-spacing: -0.02em;
}

.form-lead {
  margin-top: 4px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-sm);
}

.login-error {
  margin: 2px 0 14px;
}

.login-submit {
  width: 100%;
  height: 38px;
  margin-top: 4px;
}

.register-link {
  margin: 10px 0 0;
  font-size: 13px;
  text-align: center;
  color: var(--lpp-text-mute);
}

.form-notice {
  margin-top: 12px;
}

.demo-hint {
  margin-top: 18px;
  color: var(--lpp-text-muted);
  font-size: 12px;
  text-align: center;
}

.demo-hint code {
  color: var(--lpp-text);
}

.demo-link {
  margin-top: 6px;
  font-size: 12px;
  text-align: center;
}

.form-foot {
  width: min(360px, 100%);
  margin: 36px auto 0;
  color: var(--lpp-text-muted);
  font-size: 12px;
  text-align: center;
}

@media (max-width: 980px) {
  .auth {
    grid-template-columns: minmax(0, 1fr);
  }

  .auth-story {
    min-height: 240px;
    gap: 18px;
    padding: 26px 28px;
  }

  .story-body {
    margin-top: 6px;
  }

  .story-body h1 {
    font-size: clamp(26px, 6vw, 34px);
  }

  .story-lead {
    margin-top: 10px;
  }

  .story-rules {
    display: none;
  }

  .story-art {
    right: -30px;
    bottom: -20px;
    width: 46%;
  }

  .story-foot {
    margin-top: 10px;
  }

  .auth-form {
    padding: 32px 24px;
    border-top: 1px solid var(--lpp-border);
    border-left: 0;
  }

  .form-foot {
    margin-top: 28px;
  }
}

@media (max-width: 480px) {
  .story-foot span:first-child {
    display: none;
  }

  .auth-form {
    padding: 26px 20px;
  }
}
</style>
