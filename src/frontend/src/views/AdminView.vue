<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { createBackup, backupDownloadUrl, listBackups, restoreBackup } from '@/api/backups'
import { createUser, listUsers, type UserQuery } from '@/api/users'
import { exportAuditCsv, listAudit, type AuditQuery } from '@/api/audit'
import { listDeletionRequests, resolveDeletionRequest, type DeletionRequest } from '@/api/deletions'
import { getOpsMetrics } from '@/api/metrics'
import type { AuditItem, Role, UserItem } from '@/api/models'
import { useApiRequest } from '@/composables/useApiRequest'
import { useMeta } from '@/composables/useMeta'
import { saveBlob } from '@/utils/download'

const tab = ref<'users' | 'audit' | 'ops' | 'deletion' | 'backup'>('users')

const userFilters = reactive<UserQuery>({ page: 1, pageSize: 20, q: '', role: undefined })
const users = useApiRequest(() => listUsers({ ...userFilters }), { immediate: true })
const userRows = computed<UserItem[]>(() => users.data.value?.items ?? [])
const userTotal = computed(() => users.data.value?.total ?? 0)

const auditFilters = reactive<AuditQuery>({ page: 1, pageSize: 20, action: '' })
const audit = useApiRequest(() => listAudit({ ...auditFilters }), { immediate: false })
const ops = useApiRequest(() => getOpsMetrics(), { immediate: false })
const deletions = useApiRequest(() => listDeletionRequests('pending'), { immediate: false })
const backups = useApiRequest(() => listBackups(), { immediate: false })
const auditRows = computed<AuditItem[]>(() => audit.data.value?.items ?? [])
const auditTotal = computed(() => audit.data.value?.total ?? 0)

const createOpen = ref(false)
const creating = ref(false)
const createError = ref('')
const form = reactive({ username: '', displayName: '', role: 'teacher' as Role, password: '', group: '' })

const auditError = ref('')

function switchTab(next: 'users' | 'audit' | 'ops' | 'deletion' | 'backup'): void {
  tab.value = next
  if (next === 'audit' && !audit.data.value) void audit.load()
  if (next === 'ops' && !ops.data.value) void ops.load()
  if (next === 'deletion' && !deletions.data.value) void deletions.load()
  if (next === 'backup' && !backups.data.value) void backups.load()
}

async function makeBackup(): Promise<void> {
  let label = ''
  try {
    const result = await ElMessageBox.prompt('快照标签（可留空）', '创建备份', { confirmButtonText: '创建', cancelButtonText: '取消' })
    label = result.value || ''
  } catch {
    return
  }
  try {
    await createBackup(label)
    ElMessage.success('备份已创建')
    await backups.load()
  } catch (caught) {
    ElMessage.error(caught instanceof Error ? caught.message : '创建备份失败')
  }
}

function downloadBackup(name: string): void {
  window.open(backupDownloadUrl(name), '_blank', 'noopener')
}

async function restoreFromBackup(name: string): Promise<void> {
  try {
    await ElMessageBox.confirm(`从 ${name} 恢复到 staging 目录？当前数据不会被直接覆盖。`, '恢复备份', {
      type: 'warning',
      confirmButtonText: '恢复',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    const result = await restoreBackup(name)
    ElMessage.success(`已恢复到 ${result.target}`)
  } catch (caught) {
    ElMessage.error(caught instanceof Error ? caught.message : '恢复失败')
  }
}

async function resolveDeletion(row: DeletionRequest, approve: boolean): Promise<void> {
  try {
    await ElMessageBox.confirm(
      approve ? `批准删除《${row.contentTitle}》？批准后教案软删除但保留审计。` : `驳回《${row.contentTitle}》的删除申请？`,
      approve ? '批准删除' : '驳回申请',
      { type: 'warning', confirmButtonText: approve ? '批准' : '驳回', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await resolveDeletionRequest(row.requestId, approve)
    ElMessage.success(approve ? '已批准并软删除' : '已驳回')
    await deletions.load()
  } catch (caught) {
    ElMessage.error(caught instanceof Error ? caught.message : '处理失败')
  }
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
      <el-tab-pane label="运维" name="ops">
        <div v-loading="ops.loading.value" class="ops-panel">
          <el-alert
            v-if="ops.error.value"
            type="error"
            :closable="false"
            show-icon
            :title="ops.error.value.message"
          />
          <div v-if="ops.data.value" class="ops-grid">
            <article class="ops-card">
              <p class="ops-card__label">导出失败率</p>
              <p class="ops-card__value">{{ (ops.data.value.export.failureRate * 100).toFixed(1) }}%</p>
              <p class="ops-card__hint">失败 {{ ops.data.value.export.failed }} / 共 {{ ops.data.value.export.total }}</p>
            </article>
            <article class="ops-card">
              <p class="ops-card__label">同步冲突率</p>
              <p class="ops-card__value">{{ (ops.data.value.sync.conflictRate * 100).toFixed(1) }}%</p>
              <p class="ops-card__hint">冲突 {{ ops.data.value.sync.conflicts }} / 共 {{ ops.data.value.sync.total }}</p>
            </article>
            <article class="ops-card">
              <p class="ops-card__label">日志保留</p>
              <p class="ops-card__value">{{ ops.data.value.logRetentionDays }} 天</p>
            </article>
            <article class="ops-card">
              <p class="ops-card__label">统计时间</p>
              <p class="ops-card__value ops-card__value--small">{{ ops.data.value.generatedAt }}</p>
            </article>
          </div>
          <div v-if="ops.data.value?.alerts.length" class="ops-alerts">
            <el-alert
              v-for="alert in ops.data.value.alerts"
              :key="alert.code"
              type="warning"
              :closable="false"
              show-icon
              :title="alert.message"
            />
          </div>
          <div v-else-if="!ops.loading.value" class="empty">暂无运维指标</div>
        </div>
      </el-tab-pane>
      <el-tab-pane label="删除申请" name="deletion">
        <div v-loading="deletions.loading.value" class="deletion-panel">
          <el-alert
            v-if="deletions.error.value"
            type="error"
            :closable="false"
            show-icon
            :title="deletions.error.value.message"
          />
          <el-table v-if="deletions.data.value?.items.length" :data="deletions.data.value.items" row-key="requestId" stripe>
            <el-table-column prop="contentTitle" label="教案" min-width="180" />
            <el-table-column prop="requester" label="申请人" width="110" />
            <el-table-column prop="reason" label="原因" min-width="180" />
            <el-table-column prop="dueAt" label="应处理时间" width="190" />
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button type="danger" link @click="resolveDeletion(row, true)">批准</el-button>
                <el-button link @click="resolveDeletion(row, false)">驳回</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-else-if="!deletions.loading.value" class="empty">暂无待处理删除申请</div>
        </div>
      </el-tab-pane>
      <el-tab-pane label="备份" name="backup">
        <div v-loading="backups.loading.value" class="backup-panel">
          <div class="backup-actions">
            <el-button type="primary" @click="makeBackup">创建备份</el-button>
          </div>
          <el-alert
            v-if="backups.error.value"
            type="error"
            :closable="false"
            show-icon
            :title="backups.error.value.message"
          />
          <el-table v-if="backups.data.value?.items.length" :data="backups.data.value.items" row-key="name" stripe>
            <el-table-column prop="name" label="快照" min-width="220" />
            <el-table-column prop="createdAt" label="创建时间" width="200" />
            <el-table-column prop="schemaVersion" label="结构版本" width="90" />
            <el-table-column label="操作" width="220">
              <template #default="{ row }">
                <el-button link type="primary" @click="downloadBackup(row.name)">下载</el-button>
                <el-button link type="warning" @click="restoreFromBackup(row.name)">恢复</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-else-if="!backups.loading.value" class="empty">暂无备份</div>
        </div>
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

.backup-panel {
  display: grid;
  gap: 12px;
  padding-top: 12px;
}

.backup-actions {
  display: flex;
  justify-content: flex-end;
}

.deletion-panel {
  padding-top: 12px;
}

.ops-panel {
  padding-top: 12px;
}

.ops-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.ops-card {
  padding: 16px;
  border: 1px solid var(--lpp-border);
  border-radius: 10px;
  background: var(--lpp-surface);
}

.ops-card__label {
  margin: 0;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-sm);
}

.ops-card__value {
  margin: 8px 0 4px;
  color: var(--lpp-text);
  font-size: 26px;
  font-weight: 650;
}

.ops-card__value--small {
  font-size: var(--lpp-font-sm);
  font-weight: 500;
}

.ops-card__hint {
  margin: 0;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.ops-alerts {
  display: grid;
  gap: 8px;
  margin-top: 12px;
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
