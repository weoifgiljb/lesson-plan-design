<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'

import BrandMark from '@/components/BrandMark.vue'
import { changePassword } from '@/api/auth'
import { RequestError } from '@/api/client-error'
import { passwordValidator } from '@/utils/password'
import { useSessionStore } from '@/stores/session'

const router = useRouter()
const session = useSessionStore()

const formRef = ref<FormInstance>()
const form = reactive({
  oldPassword: '',
  newPassword: '',
  confirm: '',
})
const loading = ref(false)
const errorMessage = ref('')
const errorTrace = ref('')
const errorRef = ref<{ $el?: HTMLElement } | null>(null)

const rules: FormRules = {
  oldPassword: [{ required: true, message: '请输入当前口令', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新口令', trigger: 'blur' },
    { validator: passwordValidator, trigger: ['blur', 'change'] },
    {
      validator: (_rule, value: string, callback: (error?: Error) => void) => {
        if (value && value === form.oldPassword) callback(new Error('新口令不能与当前口令相同'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
  confirm: [
    { required: true, message: '请再次输入新口令', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback: (error?: Error) => void) => {
        if (value !== form.newPassword) callback(new Error('两次输入的口令不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

async function signOut(): Promise<void> {
  await session.signOut()
  await router.push('/login')
}

async function submit(): Promise<void> {
  if (!formRef.value) return
  errorMessage.value = ''
  errorTrace.value = ''
  formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await changePassword({
        oldPassword: form.oldPassword,
        newPassword: form.newPassword,
      })
      // 改密后旧会话/旧令牌失效，统一回登录页重新登录
      await session.signOut()
      await router.push({ path: '/login', query: { changed: '1' } })
    } catch (caught) {
      if (caught instanceof RequestError) {
        errorMessage.value = caught.message
        errorTrace.value = caught.traceId
        errorRef.value?.$el?.focus?.()
      } else {
        errorMessage.value = '修改口令失败，请检查网络或稍后重试。'
      }
    } finally {
      loading.value = false
    }
  })
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-card" aria-label="修改口令">
      <header class="card-head">
        <BrandMark caption="平台端 v1.1" :size="28" />
        <h1>修改口令</h1>
        <p class="card-lead">
          首次登录或口令到期后需要先设置新口令；修改成功后需要重新登录。
        </p>
      </header>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        :aria-describedby="errorMessage ? 'password-error' : undefined"
        @submit.prevent="submit"
      >
        <el-form-item label="当前口令" prop="oldPassword">
          <el-input
            v-model="form.oldPassword"
            type="password"
            show-password
            autocomplete="current-password"
            placeholder="请输入当前口令"
          />
        </el-form-item>
        <el-form-item label="新口令" prop="newPassword">
          <el-input
            v-model="form.newPassword"
            type="password"
            show-password
            autocomplete="new-password"
            placeholder="至少 8 位，含字母与数字"
          />
        </el-form-item>
        <el-form-item label="确认新口令" prop="confirm">
          <el-input
            v-model="form.confirm"
            type="password"
            show-password
            autocomplete="new-password"
            placeholder="再次输入新口令"
          />
        </el-form-item>

        <el-alert
          v-if="errorMessage"
          ref="errorRef"
          id="password-error"
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
          保存新口令
        </el-button>
      </el-form>

      <p class="card-foot">
        需要换个账号？<el-button link type="primary" @click="signOut">退出登录</el-button>
      </p>
    </section>
  </main>
</template>

<style scoped>
.auth-page {
  display: grid;
  place-items: center;
  min-height: 100vh;
  padding: 32px 16px;
  background: var(--lpp-surface);
}

.auth-card {
  width: min(420px, 100%);
  padding: 28px 28px 20px;
  border: 1px solid var(--lpp-border);
  border-radius: 14px;
  background: var(--lpp-surface);
  box-shadow: var(--lpp-shadow-flyout);
}

.card-head {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 18px;
}

.card-head h1 {
  margin: 0;
  font-size: 20px;
  color: var(--lpp-text);
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
}

.card-foot {
  margin: 14px 0 0;
  font-size: 13px;
  text-align: center;
  color: var(--lpp-text-muted);
}
</style>
