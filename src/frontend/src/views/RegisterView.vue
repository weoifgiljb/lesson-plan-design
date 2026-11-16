<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'

import BrandMark from '@/components/BrandMark.vue'
import { register } from '@/api/auth'
import { RequestError } from '@/api/client-error'
import { passwordValidator } from '@/utils/password'

const router = useRouter()

const formRef = ref<FormInstance>()
const form = reactive({
  username: '',
  displayName: '',
  password: '',
  confirm: '',
})
const loading = ref(false)
const errorMessage = ref('')
const errorTrace = ref('')
const errorRef = ref<{ $el?: HTMLElement } | null>(null)
const done = ref(false)

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    // 与后端 user_rules.USERNAME_MIN/MAX 保持一致（注册页匿名，取不到 /meta）
    { min: 3, max: 40, message: '用户名 3–40 位，可用字母、数字、下划线', trigger: 'blur' },
    {
      pattern: /^[A-Za-z0-9_.-]+$/,
      message: '用户名只能包含字母、数字、下划线、点或横线',
      trigger: 'blur',
    },
  ],
  displayName: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入口令', trigger: 'blur' },
    { validator: passwordValidator, trigger: ['blur', 'change'] },
  ],
  confirm: [
    { required: true, message: '请再次输入口令', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback: (error?: Error) => void) => {
        if (value !== form.password) callback(new Error('两次输入的口令不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

async function submit(): Promise<void> {
  if (!formRef.value) return
  errorMessage.value = ''
  errorTrace.value = ''
  formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await register({
        username: form.username.trim(),
        displayName: form.displayName.trim(),
        password: form.password,
      })
      done.value = true
      await router.push({ path: '/login', query: { registered: '1' } })
    } catch (caught) {
      if (caught instanceof RequestError) {
        errorMessage.value = caught.message
        errorTrace.value = caught.traceId
        errorRef.value?.$el?.focus?.()
      } else {
        errorMessage.value = '注册失败，请检查网络或稍后重试。'
      }
    } finally {
      loading.value = false
    }
  })
}
</script>

<template>
  <main class="auth-page">
    <aside class="auth-aside" aria-label="注册说明">
      <BrandMark inverse :size="30" caption="平台端 v2.0" />
      <p class="aside-kicker">教师账号 · 首次设置</p>
      <h1>领一份<br />自己的教案本。</h1>
      <ol class="aside-steps">
        <li><em>01</em><span>注册账号，填写用于展示的姓名。</span></li>
        <li><em>02</em><span>首次登录设置新口令，旧口令即失效。</span></li>
        <li><em>03</em><span>教研组由管理员分配，注册时无需选择。</span></li>
      </ol>
      <p class="aside-foot">东莞经贸学校 / 计算机教研组</p>
    </aside>

    <section class="auth-card" aria-label="注册">
      <header class="card-head">
        <p class="card-kicker">教师注册</p>
        <h1>建立你的案头</h1>
        <p class="card-lead">
          注册后首次登录需要先设置新口令；教研组由管理员分配，注册时无需填写。
        </p>
      </header>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        :aria-describedby="errorMessage ? 'register-error' : undefined"
        @submit.prevent="submit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" autocomplete="username" placeholder="例如 zhanglaoshi" />
        </el-form-item>
        <el-form-item label="姓名" prop="displayName">
          <el-input v-model="form.displayName" autocomplete="name" placeholder="用于展示的姓名" />
        </el-form-item>
        <el-form-item label="口令" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            autocomplete="new-password"
            placeholder="至少 8 位，含字母与数字"
          />
        </el-form-item>
        <el-form-item label="确认口令" prop="confirm">
          <el-input
            v-model="form.confirm"
            type="password"
            show-password
            autocomplete="new-password"
            placeholder="再次输入口令"
          />
        </el-form-item>

        <el-alert
          v-if="errorMessage"
          ref="errorRef"
          id="register-error"
          tabindex="-1"
          class="form-error"
          role="alert"
          aria-live="assertive"
          type="error"
          :closable="false"
          show-icon
          :title="errorMessage"
          :description="errorTrace ? `traceId: ${errorTrace}` : ''"
        />

        <el-button class="submit" type="primary" native-type="submit" :loading="loading">
          注册
        </el-button>
      </el-form>

      <div class="card-foot">
        <span>已有账号？</span>
        <el-button link type="primary" @click="router.push('/login')">返回登录</el-button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.auth-page {
  display: grid;
  grid-template-columns: minmax(0, 42%) minmax(0, 58%);
  min-height: 100vh;
  background: var(--lpp-surface);
}

.auth-aside {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 38px 40px 30px;
  overflow: hidden;
  background: var(--lpp-nameplate);
  color: var(--lpp-nameplate-text);
}

.auth-aside::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.05;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='140' height='140' filter='url(%23n)'/%3E%3C/svg%3E");
}

.auth-aside .brand-mark,
.aside-kicker,
.auth-aside h1,
.aside-steps,
.aside-foot {
  position: relative;
  z-index: 1;
}

.aside-kicker {
  margin-top: 28px;
  color: var(--lpp-accent);
  font-family: var(--lpp-font-hand);
  font-size: var(--lpp-font-sm);
  letter-spacing: 0.12em;
}

.auth-aside h1 {
  color: var(--lpp-nameplate-text);
  font-family: var(--lpp-font-display);
  font-size: clamp(34px, 3.8vw, 44px);
  font-weight: 600;
  line-height: 1.18;
  letter-spacing: 0.01em;
}

.aside-steps {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin: 22px 0 0;
  padding: 0;
  list-style: none;
}

.aside-steps li {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 10px;
  padding: 11px 0;
  border-bottom: 1px solid rgba(247, 241, 228, 0.14);
  color: var(--lpp-nameplate-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.55;
}

.aside-steps em {
  color: var(--lpp-accent);
  font-family: var(--lpp-font-numeric);
  font-style: normal;
  letter-spacing: 0.08em;
}

.aside-foot {
  margin-top: auto;
  color: var(--lpp-nameplate-muted);
  font-size: 12px;
}

.auth-card {
  align-self: center;
  width: min(440px, 100%);
  margin: 32px auto;
  padding: 30px 30px 22px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
  box-shadow: var(--lpp-shadow-paper);
}

.card-head {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 18px;
}

.card-head::before {
  content: '';
  display: block;
  width: 30px;
  height: 2px;
  margin-bottom: 4px;
  background: var(--lpp-accent);
}

.card-kicker {
  color: var(--lpp-accent-ink);
  font-family: var(--lpp-font-hand);
  font-size: var(--lpp-font-xs);
  letter-spacing: 0.1em;
}

.card-head h1 {
  margin: 0;
  color: var(--lpp-text);
  font-family: var(--lpp-font-display);
  font-size: var(--lpp-font-xl);
  font-weight: 600;
  letter-spacing: 0.01em;
}

.card-lead {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--lpp-text-muted);
}

.form-error {
  margin-bottom: 12px;
}

.submit {
  width: 100%;
  height: 40px;
}

.auth-card :deep(.el-form-item__label) {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.auth-card :deep(.el-input__wrapper) {
  min-height: 34px;
  border-radius: var(--lpp-radius-control);
  box-shadow: 0 0 0 1px var(--lpp-border) inset;
}

.card-foot {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  margin: 14px 0 0;
  font-size: 13px;
  color: var(--lpp-text-muted);
}

@media (max-width: 980px) {
  .auth-page {
    grid-template-columns: minmax(0, 1fr);
  }

  .auth-aside {
    min-height: 220px;
    padding: 26px 28px 22px;
  }

  .aside-kicker {
    margin-top: 16px;
  }

  .aside-steps {
    display: none;
  }

  .auth-aside h1 {
    font-size: clamp(28px, 7vw, 36px);
  }

  .aside-foot {
    margin-top: 12px;
  }

  .auth-card {
    margin: 24px auto;
  }
}

@media (max-width: 480px) {
  .auth-aside {
    min-height: 190px;
  }

  .auth-card {
    width: calc(100% - 24px);
    padding: 24px 20px 18px;
  }

  .aside-foot {
    display: none;
  }
}
</style>
