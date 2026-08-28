<script setup lang="ts">
import { computed, nextTick, onMounted, onBeforeUnmount, ref } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { Icon } from '@iconify/vue'
import AppPage from '../../components/common/AppPage.vue'
import StatusBadge from '../../components/common/StatusBadge.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import ErrorState from '../../components/common/ErrorState.vue'
import { getDashboardSummary } from '../../api/dashboard'
import type { DashboardSummary } from '../../types/clinical'
import { useAuthStore } from '../../stores/auth'
import { formatDateTime } from '../../utils/format'

echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])
const auth = useAuthStore(); const data = ref<DashboardSummary | null>(null); const loading = ref(true); const error = ref(''); const chartEl = ref<HTMLElement>(); let chart: echarts.ECharts | null = null
const greeting = computed(() => { const hour = new Date().getHours(); return hour < 12 ? '上午好' : hour < 18 ? '下午好' : '晚上好' })
const metrics = computed(() => data.value ? [
  { label: '今日病例', value: data.value.today_cases, icon: 'solar:clipboard-list-linear', tone: 'blue' },
  { label: '待审核', value: data.value.pending_reviews, icon: 'solar:clock-circle-linear', tone: 'amber' },
  { label: '高风险', value: data.value.high_risk_cases, icon: 'solar:danger-triangle-linear', tone: 'orange' },
  { label: '已完成', value: data.value.completed_cases, icon: 'solar:check-circle-linear', tone: 'green' },
] : [])
async function load() { loading.value = true; error.value = ''; try { data.value = await getDashboardSummary(); await nextTick(); draw() } catch { error.value = '无法获取工作台统计' } finally { loading.value = false } }
function draw() { if (!chartEl.value || !data.value) return; chart?.dispose(); chart = echarts.init(chartEl.value); chart.setOption({ grid: { left: 32, right: 18, top: 20, bottom: 28 }, tooltip: { trigger: 'axis' }, xAxis: { type: 'category', data: data.value.trend.map(i => i.date.slice(5)), axisLine: { lineStyle: { color: '#e7eaf0' } }, axisLabel: { color: '#98a2b3' } }, yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: '#eef1f5' } }, axisLabel: { color: '#98a2b3' } }, series: [{ type: 'line', data: data.value.trend.map(i => i.count), smooth: true, symbolSize: 7, lineStyle: { color: '#2563eb', width: 3 }, itemStyle: { color: '#2563eb' }, areaStyle: { color: 'rgba(37,99,235,.08)' } }] }) }
const resize = () => chart?.resize(); onMounted(() => { load(); addEventListener('resize', resize) }); onBeforeUnmount(() => { chart?.dispose(); removeEventListener('resize', resize) })
</script>
<template>
  <AppPage :title="`${greeting}，${auth.user?.name || '医生'}`" :description="`今天有 ${data?.pending_reviews || 0} 个 AI 辅助病例等待您处理。`">
    <el-skeleton v-if="loading" :rows="8" animated /><ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else-if="data">
      <section class="metrics"><article v-for="item in metrics" :key="item.label" class="metric surface"><span :class="['metric-icon', item.tone]"><Icon :icon="item.icon" /></span><div><small>{{ item.label }}</small><strong>{{ item.value }}</strong><p>实时业务统计</p></div></article></section>
      <section class="dashboard-grid">
        <article class="surface panel pending"><header><div><h2 class="section-title">我的待审核病例</h2><p class="section-subtitle">按临床风险与等待时间排序</p></div><router-link to="/reviews">查看全部 →</router-link></header>
          <div v-if="data.pending_items.length" class="pending-list"><router-link v-for="item in data.pending_items" :key="item.id" :to="`/cases/${item.id}`"><StatusBadge type="risk" :value="item.risk_level" /><div><strong>{{ item.patient_name }}</strong><span>{{ item.question }}</span></div><time>{{ formatDateTime(item.ai_completed_at) }}</time></router-link></div><EmptyState v-else title="暂无待审核病例" description="新的 AI 辅助意见会出现在这里" />
        </article>
        <article class="surface panel risk-panel"><header><div><h2 class="section-title">风险提醒</h2><p class="section-subtitle">需优先关注的临床风险</p></div></header>
          <div v-if="data.high_risk_cases" class="risk-callout"><Icon icon="solar:danger-triangle-linear" /><strong>{{ data.high_risk_cases }} 个高风险病例</strong><p>请优先完成临床评估，不应仅等待 AI 分析结论。</p><router-link to="/cases?risk=high">查看高风险病例</router-link></div><EmptyState v-else title="当前无高风险提醒" />
        </article>
        <article class="surface panel trend"><header><div><h2 class="section-title">近 7 日病例趋势</h2><p class="section-subtitle">AI 辅助病例创建数量</p></div></header><div ref="chartEl" class="chart" /></article>
      </section>
    </template>
  </AppPage>
</template>
<style scoped lang="scss">
.metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 18px; }.metric { padding: 20px; display: flex; align-items: center; gap: 16px; }.metric-icon { width: 46px; height: 46px; border-radius: 12px; display: grid; place-items: center; font-size: 23px; }.blue { background: #eff6ff; color: var(--primary); }.amber { background: #fffaeb; color: var(--risk-medium); }.orange { background: #fff4ed; color: var(--risk-high); }.green { background: #ecfdf3; color: var(--risk-low); }.metric div { display: grid; grid-template-columns: auto auto; align-items: baseline; column-gap: 8px; }.metric small { grid-column: 1 / -1; color: var(--text-secondary); }.metric strong { font-size: 28px; margin-top: 5px; }.metric p { margin: 0; color: var(--text-tertiary); font-size: 11px; }
.dashboard-grid { display: grid; grid-template-columns: 1.7fr 1fr; gap: 18px; }.panel { padding: 20px; min-height: 300px; }.panel header { display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px; }.panel header a { font-size: 13px; color: var(--primary); }.pending-list a { display: grid; grid-template-columns: 86px 1fr auto; gap: 12px; align-items: center; padding: 14px 4px; border-bottom: 1px solid var(--border); }.pending-list a:last-child { border: 0; }.pending-list div { display: grid; gap: 4px; min-width: 0; }.pending-list span { color: var(--text-secondary); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }.pending-list time { color: var(--text-tertiary); font-size: 11px; }.risk-callout { margin-top: 22px; padding: 20px; background: #fff7ed; border-radius: 10px; color: #9a3412; }.risk-callout svg { font-size: 25px; }.risk-callout strong { display: block; margin: 10px 0 7px; }.risk-callout p { font-size: 13px; line-height: 1.6; }.risk-callout a { font-weight: 650; font-size: 13px; }.trend { grid-column: 1 / -1; }.chart { height: 260px; }
@media (max-width: 1100px) { .metrics { grid-template-columns: repeat(2, 1fr); }.dashboard-grid { grid-template-columns: 1fr; }.trend { grid-column: auto; } }
@media (max-width: 600px) { .metrics { grid-template-columns: 1fr; }.pending-list a { grid-template-columns: 80px 1fr; }.pending-list time { display: none; } }
</style>
