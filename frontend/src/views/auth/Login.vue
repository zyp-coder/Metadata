<template>
  <div class="login-page">
    <div class="login-card">
      <h2 class="login-title">主数据管理平台</h2>
      <a-form :model="form" layout="vertical" @finish="handleLogin">
        <a-form-item label="用户名" name="username" :rules="[{ required: true, message: '请输入用户名' }]">
          <a-input v-model:value="form.username" placeholder="请输入用户名" :maxlength="64" />
        </a-form-item>
        <a-form-item label="密码" name="password" :rules="[{ required: true, message: '请输入密码' }]">
          <a-input-password v-model:value="form.password" placeholder="请输入密码" @pressEnter="handleLogin" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" :loading="loading" block>登 录</a-button>
        </a-form-item>
      </a-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { loginApi } from '@/api/auth'
import { extractApiError } from '@/utils/apiError'

const router = useRouter()
const loading = ref(false)
const form = reactive({
  username: '',
  password: '',
})

async function handleLogin() {
  if (!form.username || !form.password) {
    message.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const { data } = await loginApi(form)
    localStorage.setItem('token', data.token)
    message.success('登录成功')
    router.push('/')
  } catch (e: any) {
    // C10：登录失败统一文案，不泄露账号是否存在
    const msg = e?.response?.status === 401
      ? '用户名或密码错误'
      : (extractApiError(e) || '登录失败')
    message.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
}
.login-card {
  width: 400px;
  padding: 40px 32px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.login-title {
  text-align: center;
  margin-bottom: 32px;
  font-size: 22px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
}
</style>
