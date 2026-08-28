import { reactive } from 'vue'

export function usePagination(pageSize = 20) {
  /** 创建列表页通用的分页状态对象。 */
  return reactive({ page: 1, page_size: pageSize, total: 0 })
}
