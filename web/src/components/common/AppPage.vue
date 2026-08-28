<script setup lang="ts">
defineProps<{ title: string; description?: string }>()
</script>
<template>
  <main class="page-shell">
    <header class="page-heading">
      <div><h1>{{ title }}</h1><p v-if="description">{{ description }}</p></div>
      <div><slot name="actions" /></div>
    </header>
    <slot />
  </main>
</template>
