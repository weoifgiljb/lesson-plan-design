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
    { min: 3, max: 64, message: '用户名 3–64 位，可用字母、数字、下划线', trigger: 'blur' },
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
    <section class="auth-card" aria-label="注册">
      <header class="card-head">
        <BrandMark caption="平台端 v1.1" :size="28" />
        <h1>注册教师账号</h1>
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
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  margin: 14px 0 0;
  font-size: 13px;
  color: var(--lpp-text-muted);
}
</style>
