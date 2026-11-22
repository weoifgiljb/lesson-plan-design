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
// 开发账号由 Vite 环境变量提供（VITE_DEV_USERNAME），源码里不写死：写死会与种子账号漂移（UI-04 缺口）。
// 只预填用户名、绝不预填口令：VITE_ 变量会被构建期内联，口令放进去等于写进前端产物。
const devUsername = isDev ? String(import.meta.env.VITE_DEV_USERNAME ?? '') : ''

const formRef = ref<FormInstance>()
const usernameRef = ref<{ focus: () => void } | null>(null)
const form = reactive({
  username: devUsername,
  password: '',
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

function goRegister(): void {
  router.push('/register')
}

onMounted(() => {
  usernameRef.value?.focus()
})
</script>

<template>
  <main class="auth">
    <section class="auth-story" aria-label="平台简介">
      <div class="story-top">
        <BrandMark inverse :size="30" caption="平台端 v2.0" />
      </div>

      <div class="story-body">
        <p class="story-kicker">备课案头 · 纸墨批注</p>
        <h1>把每一份教案，<br />摊开在案头。</h1>
        <p class="story-lead">
          三维目标、八步流程与证据链，落在同一张工作台上。写完、审完、导出，不用换工具。
        </p>

        <ul class="story-rules">
          <li>
            <em>01</em>
            <strong>结构可校验</strong>
            <span>校标字段、八步流程与分钟合计，导入即校验。</span>
          </li>
          <li>
            <em>02</em>
            <strong>证据可追溯</strong>
            <span>哈希、轮次、放行记录与审查状态，五项逐条对照。</span>
          </li>
          <li>
            <em>03</em>
            <strong>版本可回滚</strong>
            <span>每次修订留下版本链与差异，导出的 DOCX 带哈希。</span>
          </li>
        </ul>
      </div>

      <figure class="story-art-frame" aria-hidden="true">
        <svg viewBox="0 0 320 400" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round">
          <path d="M58 118l150-34 54 214-150 38z" opacity="0.9" />
          <path d="M76 128l126-30 42 178-126 34z" opacity="0.55" />
          <path d="M94 151l88-21M101 180l88-21M108 209l82-20M115 238l70-17M122 267l64-15" opacity="0.55" />
          <path d="M214 256c26-8 46 2 50 22 4 20-10 34-34 38-18 3-30-5-34-20-4-14 2-30 18-40z" opacity="0.85" />
          <path d="M226 273l22 18M248 269l-20 22" opacity="0.7" />
          <path d="M58 342c34-10 66-8 96 4M70 362c30-7 58-5 84 4" opacity="0.45" />
          <path d="M214 100l24-8 32 96-24 8z" opacity="0.6" />
          <path d="M238 92l10-4 8 22-10 4z" opacity="0.9" />
        </svg>
        <figcaption>备课案头 · 教案本 / 朱笔 / 印章</figcaption>
      </figure>

      <div class="story-foot">
        <span>东莞经贸学校 / 计算机教研组</span>
        <span class="mono">LPP / v2.0.0</span>
      </div>
    </section>

    <section class="auth-form" aria-label="登录">
      <div class="form-inner">
        <div class="form-head">
          <h2>回到案头</h2>
          <p class="form-lead">用学校账号登录，继续今天的教案。</p>
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

          <div class="auth-actions">
            <el-button class="login-submit" type="primary" native-type="submit" :loading="loading">
              登录
            </el-button>
            <el-button class="register-submit" native-type="button" @click="goRegister">
              注册新账号
            </el-button>
          </div>
        </el-form>

        <el-alert
          v-if="route.query.registered || route.query.changed"
          class="form-notice"
          type="success"
          :closable="false"
          show-icon
          :title="route.query.changed ? '口令已更新，请用新口令登录。' : '注册成功，请用新账号登录并设置新口令。'"
        />
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
  gap: 28px;
  padding: 38px 44px 30px;
  overflow: hidden;
  background: var(--lpp-nameplate);
  color: var(--lpp-nameplate-text);
}

.auth-story::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.05;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='140' height='140' filter='url(%23n)'/%3E%3C/svg%3E");
}

.story-kicker {
  margin-bottom: 14px;
  color: var(--lpp-accent-on-dark);
  font-family: var(--lpp-font-hand);
  font-size: var(--lpp-font-sm);
  letter-spacing: 0.12em;
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
  font-family: var(--lpp-font-display);
  font-size: clamp(38px, 4.4vw, 46px);
  font-weight: 600;
  line-height: 1.18;
  letter-spacing: 0.01em;
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
  max-width: 430px;
  margin: 30px 0 0;
  padding: 0;
  list-style: none;
}

.story-rules li {
  display: grid;
  grid-template-columns: 30px 96px minmax(0, 1fr);
  gap: 10px;
  padding: 11px 0;
  border-bottom: 1px solid rgba(247, 241, 228, 0.14);
}

.story-rules em {
  color: var(--lpp-accent-on-dark);
  font-family: var(--lpp-font-numeric);
  font-size: 11px;
  font-style: normal;
  letter-spacing: 0.08em;
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

.story-art-frame {
  position: absolute;
  right: 30px;
  bottom: 82px;
  width: min(33%, 270px);
  margin: 0;
  padding: 9px 9px 6px;
  border: 1px solid rgba(247, 241, 228, 0.5);
  background: var(--lpp-surface);
  box-shadow: var(--lpp-shadow-paper);
  transform: rotate(-1.5deg);
  pointer-events: none;
}

.story-art-frame svg {
  display: block;
  width: 100%;
  height: auto;
  color: var(--lpp-nameplate);
  opacity: 0.78;
}

.story-art-frame figcaption {
  margin-top: 4px;
  color: var(--lpp-brass-ink);
  font-family: var(--lpp-font-hand);
  font-size: 10px;
  text-align: center;
  letter-spacing: 0.04em;
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

.form-inner::before {
  content: '';
  display: block;
  width: 30px;
  height: 2px;
  margin-bottom: 18px;
  background: var(--lpp-accent);
}

.form-head {
  margin-bottom: 24px;
}

.form-head h2 {
  font-family: var(--lpp-font-display);
  font-size: var(--lpp-font-xl);
  font-weight: 600;
  letter-spacing: 0.01em;
}

.form-lead {
  margin-top: 4px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-sm);
}

.auth-form :deep(.el-form-item__label) {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.auth-form :deep(.el-input__wrapper) {
  min-height: 34px;
  border-radius: var(--lpp-radius-control);
  background: var(--lpp-surface);
  box-shadow: 0 0 0 1px var(--lpp-border) inset;
}

.auth-form :deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 1px var(--lpp-primary) inset,
    0 0 0 3px var(--lpp-focus-soft);
}

.login-error {
  margin: 2px 0 14px;
}

.login-submit {
  width: 100%;
  height: 40px;
  margin-top: 4px;
}

.auth-actions {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  align-items: center;
}

.register-submit {
  width: 100%;
  margin-left: 0;
}

.form-notice {
  margin-top: 12px;
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

@media (max-width: 1280px) {
  .story-art-frame {
    display: none;
  }
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

  .story-art-frame {
    display: none;
  }

  .story-kicker {
    margin-bottom: 8px;
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
