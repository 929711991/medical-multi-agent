<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AppPage from '../../components/common/AppPage.vue'
import ErrorState from '../../components/common/ErrorState.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { getKnowledgeDocuments, getKnowledgeStatus, type KnowledgeDocument, type KnowledgeStatus } from '../../api/knowledge'
import { formatDateTime } from '../../utils/format'

const loading = ref(true)
const error = ref('')
const status = ref<KnowledgeStatus | null>(null)
const documents = ref<KnowledgeDocument[]>([])

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [statusResult, documentResult] = await Promise.all([getKnowledgeStatus(), getKnowledgeDocuments()])
    status.value = statusResult
    documents.value = documentResult.items
  } catch {
    error.value = '医学知识库状态加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <AppPage title="医学知识" description="正式医学 RAG 知识库状态与文档版本">
    <el-skeleton v-if="loading" :rows="8" animated />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else-if="status">
      <section class="status-grid">
        <div class="surface metric"><span>RAG 状态</span><strong :class="status.rag_ready ? 'ready' : 'down'">{{ status.rag_ready ? 'READY' : 'NOT READY' }}</strong></div>
        <div class="surface metric"><span>Redis Vector</span><strong>{{ status.redis }}</strong></div>
        <div class="surface metric"><span>文档数量</span><strong>{{ status.knowledge_documents }}</strong></div>
        <div class="surface metric"><span>Embedding</span><strong class="small">{{ status.embedding_model || '未配置' }}</strong></div>
      </section>

      <el-alert v-if="!status.rag_ready" class="notice" type="warning" :closable="false" show-icon :title="status.message || 'RAG 尚未就绪'" />

      <section class="surface table-card">
        <div class="heading"><div><h3>知识文档</h3><p>Collection：<span class="mono">{{ status.collection }}</span></p></div><el-button @click="load">刷新</el-button></div>
        <EmptyState v-if="!documents.length" title="暂无已登记知识文档" description="请先执行 scripts/rag_ingest.py 将确认过的医学指南入库" />
        <el-table v-else :data="documents">
          <el-table-column prop="title" label="标题" min-width="220" />
          <el-table-column prop="source" label="来源" min-width="220" />
          <el-table-column prop="version" label="版本" width="110"><template #default="{ row }">{{ row.version || '—' }}</template></el-table-column>
          <el-table-column prop="status" label="状态" width="110" />
          <el-table-column prop="chunk_count" label="Chunk" width="90" />
          <el-table-column label="更新时间" width="175"><template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template></el-table-column>
        </el-table>
      </section>
    </template>
  </AppPage>
</template>

<style scoped lang="scss">
.status-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 16px; }
.metric { padding: 18px; display: grid; gap: 8px; }
.metric span { color: var(--text-secondary); font-size: 12px; }
.metric strong { font-size: 20px; }
.metric strong.small { font-size: 13px; word-break: break-word; }
.ready { color: var(--risk-low); }
.down { color: var(--risk-high); }
.notice { margin-bottom: 16px; }
.table-card { padding: 20px; }
.heading { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.heading h3 { margin: 0 0 5px; }
.heading p { margin: 0; color: var(--text-secondary); font-size: 12px; }
@media (max-width: 980px) { .status-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 620px) { .status-grid { grid-template-columns: 1fr; } }
</style>
