import { onBeforeUnmount, ref } from 'vue'
import type { CaseEvent } from '../types/case'

export function useCaseStream(caseId: string, onStatus: (status: string) => void) {
  /** 创建病例事件流状态，并提供连接与自动清理能力。 */
  const events = ref<CaseEvent[]>([])
  const connected = ref(false)
  let source: EventSource | null = null
  const connect = () => {
    // 重连前关闭旧连接，避免同一病例同时产生多条事件流。
    source?.close()
    source = new EventSource(`/api/v1/cases/${caseId}/events`, { withCredentials: true })
    connected.value = true
    const receive = (message: MessageEvent<string>) => {
      // 事件内容统一转换为病例事件，再同步到页面和外部状态回调。
      const item = JSON.parse(message.data) as CaseEvent
      events.value.push(item)
      if (item.event === 'case.status.changed') onStatus(item.status)
    }
    source.addEventListener('graph.node.completed', receive as EventListener)
    source.addEventListener('case.status.changed', receive as EventListener)
    source.onerror = () => { connected.value = false; source?.close() }
  }
  // 组件卸载时主动关闭长连接，避免后台继续占用浏览器连接资源。
  onBeforeUnmount(() => source?.close())
  return { events, connected, connect }
}
