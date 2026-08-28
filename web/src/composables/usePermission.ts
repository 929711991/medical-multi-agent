import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'

export function usePermission() {
  const auth = useAuthStore()
  return { canReview: computed(() => auth.user?.role === 'doctor') }
}
