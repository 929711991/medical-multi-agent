import { reactive } from 'vue'

export function usePagination(pageSize = 20) {
  return reactive({ page: 1, page_size: pageSize, total: 0 })
}
