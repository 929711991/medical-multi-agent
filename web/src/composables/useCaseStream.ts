import { onBeforeUnmount, ref } from 'vue'
import type { CaseEvent } from '../types/case'

export function useCaseStream(caseId: string, onStatus: (status: string) => void) {
  const events = ref<CaseEvent[]>([])
  const connected = ref(false)
  let source: EventSource | null = null
  const connect = () => {
    source?.close()
    source = new EventSource(`/api/v1/cases/${caseId}/events`, { withCredentials: true })
    connected.value = true
    const receive = (message: MessageEvent<string>) => {
      const item = JSON.parse(message.data) as CaseEvent
      events.value.push(item)
      if (item.event === 'case.status.changed') onStatus(item.status)
    }
    source.addEventListener('graph.node.completed', receive as EventListener)
    source.addEventListener('case.status.changed', receive as EventListener)
    source.onerror = () => { connected.value = false; source?.close() }
  }
  onBeforeUnmount(() => source?.close())
  return { events, connected, connect }
}
