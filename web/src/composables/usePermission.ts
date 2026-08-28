import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'

export function usePermission() {
  /** 根据当前医生身份提供页面权限计算值。 */
  const auth = useAuthStore()
  return { canReview: computed(() => auth.user?.role === 'doctor') }
}
