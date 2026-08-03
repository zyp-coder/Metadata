import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Domain } from '@/types'

export const useModelingStore = defineStore('modeling', () => {
  const currentDomain = ref<Domain | null>(null)

  function setCurrentDomain(domain: Domain | null) {
    currentDomain.value = domain
  }

  return { currentDomain, setCurrentDomain }
})
