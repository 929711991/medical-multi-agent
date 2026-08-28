<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppPage from '../../components/common/AppPage.vue'
import StatusBadge from '../../components/common/StatusBadge.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import ErrorState from '../../components/common/ErrorState.vue'
import PatientCreateDialog from '../../components/patient/PatientCreateDialog.vue'
import { getPatients } from '../../api/patient'
import type { Patient } from '../../types/patient'
import { formatDateTime } from '../../utils/format'
import { sexLabel } from '../../utils/medical'

const router = useRouter()
const items = ref<Patient[]>([])
const loading = ref(true)
const error = ref('')
const showCreate = ref(false)
const filters = reactive({ search: '', sex: '' })
const page = reactive({ page: 1, page_size: 20, total: 0 })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await getPatients({
      ...page,
      search: filters.search || undefined,
      sex: filters.sex || undefined,
    })
    items.value = result.items
    page.total = result.total
  } catch {
    error.value = '患者列表加载失败'
  } finally {
    loading.value = false
  }
}

function search() {
  page.page = 1
  load()
}

async function openCreatedPatient(patientId: string) {
  await router.push(`/patients/${patientId}`)
}

onMounted(load)
</script>

<template>
  <AppPage title="患者中心" description="检索患者并进入结构化临床档案">
    <template #actions>
      <el-button type="primary" @click="showCreate = true">+ 添加患者</el-button>
      <el-button @click="router.push('/cases')">查看 AI 病例</el-button>
    </template>

    <section class="surface list-card">
      <div class="toolbar">
        <el-input v-model="filters.search" clearable placeholder="搜索患者姓名或编号" style="width: 300px" @keyup.enter="search" />
        <el-select v-model="filters.sex" clearable placeholder="性别" style="width: 130px">
          <el-option label="男" value="male" />
          <el-option label="女" value="female" />
          <el-option label="其他" value="other" />
        </el-select>
        <el-button type="primary" @click="search">查询</el-button>
      </div>

      <el-skeleton v-if="loading" :rows="7" animated />
      <ErrorState v-else-if="error" :message="error" @retry="load" />
      <EmptyState v-else-if="!items.length" title="暂无患者" description="可以点击右上角“添加患者”创建患者档案" />
      <template v-else>
        <el-table :data="items">
          <el-table-column label="患者" min-width="190">
            <template #default="{ row }">
              <div class="patient-cell">
                <span>{{ row.name.slice(-1) }}</span>
                <div><strong>{{ row.name }}</strong><small class="mono">{{ row.patient_id }}</small></div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="性别 / 年龄" width="120">
            <template #default="{ row }">{{ sexLabel(row.sex) }} · {{ row.age ?? '—' }}岁</template>
          </el-table-column>
          <el-table-column label="主要病史" min-width="220">
            <template #default="{ row }">{{ row.history.join('、') || '暂无重要病史' }}</template>
          </el-table-column>
          <el-table-column label="最近就诊" min-width="165">
            <template #default="{ row }">{{ formatDateTime(row.latest_visit) }}</template>
          </el-table-column>
          <el-table-column label="当前病例风险" width="130">
            <template #default="{ row }">
              <StatusBadge v-if="row.current_case_risk" type="risk" :value="row.current_case_risk" />
              <span v-else class="muted">无活动病例</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="router.push(`/patients/${row.patient_id}`)">查看档案</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination">
          <el-pagination v-model:current-page="page.page" :page-size="page.page_size" :total="page.total" layout="total, prev, pager, next" @current-change="load" />
        </div>
      </template>
    </section>

    <PatientCreateDialog v-model="showCreate" @created="openCreatedPatient" />
  </AppPage>
</template>

<style scoped lang="scss">
.list-card { padding: 20px; }
.patient-cell { display: flex; gap: 10px; align-items: center; }
.patient-cell > span { width: 34px; height: 34px; border-radius: 9px; background: #edf4ff; color: var(--primary); display: grid; place-items: center; font-weight: 750; }
.patient-cell div { display: grid; gap: 4px; }
.patient-cell small { color: var(--text-tertiary); }
.pagination { display: flex; justify-content: flex-end; padding-top: 18px; }
</style>
