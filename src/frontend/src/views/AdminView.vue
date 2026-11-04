<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

import { createUser, listUsers, type UserQuery } from '@/api/users'
import { exportAuditCsv, listAudit, type AuditQuery } from '@/api/audit'
import type { AuditItem, Role, UserItem } from '@/api/models'
import { useApiRequest } from '@/composables/useApiRequest'
import { useMeta } from '@/composables/useMeta'
import { saveBlob } from '@/utils/download'

const tab = ref<'users' | 'audit'>('users')

const userFilters = reactive<UserQuery>({ page: 1, pageSize: 20, q: '', role: undefined })
const users = useApiRequest(() => listUsers({ ...userFilters }), { immediate: true })
const userRows = computed<UserItem[]>(() => users.data.value?.items ?? [])
const userTotal = computed(() => users.data.value?.total ?? 0)

const auditFilters = reactive<AuditQuery>({ page: 1, pageSize: 20, action: '' })
const audit = useApiRequest(() => listAudit({ ...auditFilters }), { immediate: false })
const auditRows = computed<AuditItem[]>(() => audit.data.value?.items ?? [])
const auditTotal = computed(() => audit.data.value?.total ?? 0)

const createOpen = ref(false)
const creating = ref(false)
const createError = ref('')
const form = reactive({ username: '', displayName: '', role: 'teacher' as Role, password: '', group: '' })

const auditError = ref('')

function switchTab(next: 'users' | 'audit'): void {
  tab.value = next
  if (next === 'audit' && !audit.data.value) void audit.load()
}

async function submitCreate(): Promise<void> {
  creating.value = true
  createError.value = ''
  try {
    await createUser({
      username: form.username.trim(),
      displayName: form.displayName.trim(),
      role: form.role,
      password: form.password,
      group: form.group.trim() || undefined,
    })
    createOpen.value = false
    form.username = ''
    form.displayName = ''
    form.password = ''
    form.group = ''
    await users.load()
  } catch (caught) {
    createError.value = caught instanceof Error ? caught.message : '建号失败'
  } finally {
    creating.value = false
  }
}

async function downloadAudit(): Promise<void> {
  auditError.value = ''
  try {
    const blob = await exportAuditCsv()
    saveBlob(blob, 'audit.csv')
  } catch (caught) {
    auditError.value = caught instanceof Error ? caught.message : '导出失败'
  }
}

const { meta, loadMeta } = useMeta()
void loadMeta()

// 角色中文以后端 /meta 为准（后端是"任课教师/教研组长/系统管理员"）
const roleLabel = computed(
  () => new Map((meta.value?.roles ?? []).map((item) => [item.code, item.label])),
)
</script>

<template>
  <section class="admin">
    <header class="head">
      <div>
        <h1>管理</h1>
        <p class="lead">账号与审计：新建账号须先改密；审计只追加，不提供修改与删除。</p>
      </div>
      <el-button v-if="tab === 'users'" type="primary" @click="createOpen = true">新建账号</el-button>
      <el-button v-else @click="downloadAudit">导出审计 CSV</el-button>
    </header>

    <el-tabs :model-value="tab" @tab-change="switchTab($event as 'users' | 'audit')">
      <el-tab-pane label="账号" name="users">
        <div class="filters">
          <el-input v-model="userFilters.q" class="filter" placeholder="按姓名搜索" clearable @change="users.load()" />
          <el-select v-model="userFilters.role" class="filter" placeholder="全部角色" clearable @change="users.load()">
            <el-option value="teacher" label="教师" />
            <el-option value="lead" label="教研组长" />
            <el-option value="admin" label="管理员" />
          </el-select>
        </div>

        <el-alert v-if="users.error.value" type="error" :closable="false" show-icon :title="users.error.value.message" />

        <div class="table-wrap" v-loading="users.loading.value">
          <el-table v-if="userRows.length" :data="userRows" row-key="userId" stripe>
            <el-table-column prop="username" label="用户名" width="160" />
            <el-table-column prop="displayName" label="姓名" width="140" />
            <el-table-column label="角色" width="120">
              <template #default="{ row }">{{ roleLabel.get(row.role) ?? row.role }}</template>
            </el-table-column>
            <el-table-column prop="group" label="教研组" width="140" />
            <el-table-column label="状态" width="150">
              <template #default="{ row }">
                <el-tag :type="row.active ? 'success' : 'info'" disable-transitions>
                  {{ row.active ? '启用' : '停用' }}
                </el-tag>
                <el-tag v-if="row.mustChangePassword" class="tag" type="warning" disable-transitions>
                  待改密
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="createdAt" label="创建时间" min-width="190" />
          </el-table>
          <div v-else-if="!users.loading.value" class="empty">暂无账号</div>
        </div>

        <footer v-if="userTotal > userFilters.pageSize!" class="pager">
          <el-pagination
            v-model:current-page="userFilters.page"
            :page-size="userFilters.pageSize"
            :total="userTotal"
            layout="prev, pager, next"
            background
            @current-change="users.load()"
          />
        </footer>
      </el-tab-pane>

      <el-tab-pane label="审计" name="audit">
        <div class="filters">
          <el-input v-model="auditFilters.action" class="filter" placeholder="按动作筛选（如 task.create）" clearable @change="audit.load()" />
        </div>

        <el-alert v-if="auditError" type="error" :closable="false" show-icon :title="auditError" />
        <el-alert v-if="audit.error.value" type="error" :closable="false" show-icon :title="audit.error.value.message" />

        <div class="table-wrap" v-loading="audit.loading.value">
          <el-table v-if="auditRows.length" :data="auditRows" row-key="id" stripe>
            <el-table-column prop="createdAt" label="时间" width="190" />
            <el-table-column label="操作者" width="150">
              <template #default="{ row }">{{ row.actor.name || '系统' }}</template>
            </el-table-column>
            <el-table-column prop="action" label="动作" width="180" />
            <el-table-column label="对象" width="160">
              <template #default="{ row }">{{ row.targetType }}#{{ row.targetId }}</template>
            </el-table-column>
            <el-table-column prop="ip" label="IP" width="140" />
            <el-table-column prop="traceId" label="traceId" min-width="220" />
          </el-table>
          <div v-else-if="!audit.loading.value" class="empty">暂无审计记录</div>
        </div>

        <footer v-if="auditTotal > auditFilters.pageSize!" class="pager">
          <el-pagination
            v-model:current-page="auditFilters.page"
            :page-size="auditFilters.pageSize"
            :total="auditTotal"
            layout="prev, pager, next"
            background
            @current-change="audit.load()"
          />
        </footer>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="createOpen" title="新建账号" width="420px">
      <el-alert v-if="createError" type="error" :closable="false" show-icon :title="createError" />
      <el-form label-position="top">
        <el-form-item label="用户名"><el-input v-model="form.username" /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="form.displayName" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role">
            <el-option value="teacher" label="教师" />
            <el-option value="lead" label="教研组长" />
            <el-option value="admin" label="管理员" />
          </el-select>
        </el-form-item>
        <el-form-item label="教研组"><el-input v-model="form.group" placeholder="可留空" /></el-form-item>
        <el-form-item label="初始口令">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 8 位，含字母与数字" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createOpen = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.admin {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.head {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
  justify-content: space-between;
}

.head h1 {
  margin: 0 0 4px;
  font-size: 20px;
}

.lead {
  margin: 0;
  font-size: 13px;
  color: var(--lpp-text-muted);
}

.filters {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.filter {
  width: 220px;
}

.table-wrap {
  min-height: 220px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
}

.empty {
  display: grid;
  place-content: center;
  min-height: 200px;
  color: var(--lpp-text-muted);
  font-size: 13px;
}

.tag {
  margin-left: 6px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}
</style>
