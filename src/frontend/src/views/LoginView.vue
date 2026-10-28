<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { RequestError } from '@/api/client-error'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const form = reactive({ username: 'teacher1', password: 'Lesson2026' })
const loading = ref(false)
const error = ref('')

async function submit(): Promise<void> {
  error.value = ''
  loading.value = true
  try {
    await session.signIn(form.username, form.password)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.push(redirect)
  } catch (caught) {
    error.value = caught instanceof RequestError ? caught.message : '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-brand">
      <div class="login-mark">L</div>
      <h1>校本教案平台</h1>
      <p class="muted">收、看、审、导、统，一处完成</p>
    </div>

    <el-card class="login-card" shadow="never">
      <template #header>
        <div class="login-head">
          <h2>登录</h2>
          <router-link to="/styleguide">先看风格验收 →</router-link>
        </div>
      </template>

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password autocomplete="current-password" />
        </el-form-item>
        <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
        <el-button class="login-submit" type="primary" native-type="submit" :loading="loading">
          登录
        </el-button>
      </el-form>

      <p class="muted login-hint">本地开发默认：teacher1 / Lesson2026</p>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-content: center;
  gap: 24px;
  padding: 24px;
  background:
    radial-gradient(circle at 15% 15%, rgba(31, 58, 95, 0.08), transparent 45%),
    var(--lpp-canvas);
}

.login-brand {
  text-align: center;
}

.login-mark {
  width: 40px;
  height: 40px;
  margin: 0 auto 10px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: var(--lpp-accent);
  color: #1b1408;
  font-weight: 700;
  font-size: 20px;
}

.login-card {
  width: min(400px, 100%);
}

.login-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.login-submit {
  width: 100%;
  margin-top: 8px;
}

.login-hint {
  margin-top: 12px;
  font-size: 12px;
  text-align: center;
}
</style>
