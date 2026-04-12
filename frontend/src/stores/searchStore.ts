import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useSearchStore = defineStore('search', () => {
  // 搜索历史
  const searchHistory = ref<any[]>([])

  // 当前搜索关键词
  const currentKeywords = ref({
    skills: [] as string[],
    job_types: [] as string[],
    locations: [] as string[],
    experiences: [] as string[],
    educations: [] as string[]
  })

  // 搜索参数
  const searchParams = ref({
    page: 1,
    page_size: 10,
    sort_by: 'relevance',
    ascending: false
  })

  // 添加搜索记录
  const addSearchRecord = (keywords: any, results: any[]) => {
    const record = {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      keywords,
      result_count: results.length,
      results: results.slice(0, 3) // 只保存前3个结果
    }

    searchHistory.value.unshift(record)

    // 只保留最近10条记录
    if (searchHistory.value.length > 10) {
      searchHistory.value = searchHistory.value.slice(0, 10)
    }

    // 保存到localStorage
    localStorage.setItem('searchHistory', JSON.stringify(searchHistory.value))
  }

  // 清除搜索历史
  const clearSearchHistory = () => {
    searchHistory.value = []
    localStorage.removeItem('searchHistory')
  }

  // 设置当前关键词
  const setCurrentKeywords = (keywords: any) => {
    currentKeywords.value = keywords
    localStorage.setItem('currentKeywords', JSON.stringify(keywords))
  }

  // 从localStorage恢复数据
  const restoreFromStorage = () => {
    const storedHistory = localStorage.getItem('searchHistory')
    if (storedHistory) {
      searchHistory.value = JSON.parse(storedHistory)
    }

    const storedKeywords = localStorage.getItem('currentKeywords')
    if (storedKeywords) {
      currentKeywords.value = JSON.parse(storedKeywords)
    }
  }

  // 获取最近搜索的关键词
  const recentKeywords = computed(() => {
    return searchHistory.value.map(record => record.keywords)
  })

  return {
    searchHistory,
    currentKeywords,
    searchParams,
    addSearchRecord,
    clearSearchHistory,
    setCurrentKeywords,
    restoreFromStorage,
    recentKeywords
  }
})