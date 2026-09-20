import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

/**
 * Merge initial filters with ?key=value query params, enabling drill-down links
 * like /query?zone_id=2 or /exceedances?status=pending&manager_id=5.
 * Non-empty initial values take precedence over the default empty placeholders.
 */
export function useUrlFilters(defaults = {}) {
  const [searchParams] = useSearchParams()
  return useMemo(() => {
    const merged = { ...defaults }
    searchParams.forEach((value, key) => {
      if (key === 'page' || key === 'page_size') return
      merged[key] = value
    })
    return merged
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams])
}
