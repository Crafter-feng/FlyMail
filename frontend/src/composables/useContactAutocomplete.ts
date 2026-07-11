/** 写信自动补全 composable
 *
 * 封装联系人搜索、下拉列表显示、键盘导航逻辑。
 * to/cc/bcc 三个输入框复用同一逻辑，避免重复代码。
 */
import { ref, type Ref } from 'vue'
import { useContacts, formatContactTag, type ContactSuggestion } from './useContacts'

export function useContactAutocomplete() {
  const { searchContacts } = useContacts()

  /** 为指定输入框创建自动补全状态 */
  function createField(inputRef: Ref<string>) {
    const suggestions = ref<ContactSuggestion[]>([])
    const showSuggestions = ref(false)
    const activeIndex = ref(-1)

    let searchTimer: ReturnType<typeof setTimeout> | null = null

    /** 输入变化时触发防抖搜索 */
    function onInput() {
      if (searchTimer) clearTimeout(searchTimer)
      const val = inputRef.value.trim()

      if (val.length < 1) {
        suggestions.value = []
        showSuggestions.value = false
        activeIndex.value = -1
        return
      }

      searchTimer = setTimeout(async () => {
        try {
          suggestions.value = await searchContacts(val)
          showSuggestions.value = suggestions.value.length > 0
          activeIndex.value = -1
        } catch {
          suggestions.value = []
          showSuggestions.value = false
        }
      }, 200)
    }

    /** 关闭下拉列表 */
    function closeSuggestions() {
      showSuggestions.value = false
      activeIndex.value = -1
    }

    /**
     * 处理键盘导航
     * 返回 true 表示事件已处理（阻止默认行为），false 表示未处理
     */
    function handleKeydown(e: KeyboardEvent): { handled: boolean; selected: ContactSuggestion | null } {
      if (!showSuggestions.value || suggestions.value.length === 0) {
        return { handled: false, selected: null }
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        activeIndex.value = (activeIndex.value + 1) % suggestions.value.length
        return { handled: true, selected: null }
      }

      if (e.key === 'ArrowUp') {
        e.preventDefault()
        activeIndex.value = activeIndex.value <= 0
          ? suggestions.value.length - 1
          : activeIndex.value - 1
        return { handled: true, selected: null }
      }

      if (e.key === 'Escape') {
        closeSuggestions()
        return { handled: true, selected: null }
      }

      // 回车且下拉列表打开且有选中项时，选中当前项
      if ((e.key === 'Enter' || e.key === 'Tab') && activeIndex.value >= 0) {
        e.preventDefault()
        const selected = suggestions.value[activeIndex.value]
        closeSuggestions()
        return { handled: true, selected }
      }

      return { handled: false, selected: null }
    }

    /** 选中某个建议项，返回格式化的标签字符串 */
    function selectSuggestion(item: ContactSuggestion): string {
      closeSuggestions()
      return formatContactTag(item)
    }

    return {
      suggestions,
      showSuggestions,
      activeIndex,
      onInput,
      closeSuggestions,
      handleKeydown,
      selectSuggestion,
    }
  }

  return { createField }
}
