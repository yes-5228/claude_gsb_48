import { useCallback, useEffect, useState } from 'react'
import { areaRanking, createArea, listAreas, updateArea } from '../../api/areas.js'
import Pagination from '../../components/common/Pagination.jsx'
import { SectionCard } from '../../components/common/Card.jsx'
import { Alert } from '../../components/common/Feedback.jsx'
import { useToast } from '../../components/common/ToastProvider.jsx'
import { useAsyncData } from '../../hooks/useAsyncData.js'
import { useListQuery } from '../../hooks/useListQuery.js'
import { resetOptionCache } from '../../hooks/useOptions.js'
import AreaDetailDrawer from './components/AreaDetailDrawer.jsx'
import AreaFilters from './components/AreaFilters.jsx'
import AreaFormModal from './components/AreaFormModal.jsx'
import AreaRankingPanel from './components/AreaRankingPanel.jsx'
import AreaTable from './components/AreaTable.jsx'
import PersonsPanel from './PersonsPanel.jsx'

const INITIAL_FILTERS = { keyword: '', status: '' }
const TABS = [
  { key: 'areas', label: '片区与点位' },
  { key: 'persons', label: '责任人' }
]

export default function AreasPage() {
  const toast = useToast()
  const [tab, setTab] = useState('areas')
  const query = useListQuery(listAreas, INITIAL_FILTERS)
  const [formState, setFormState] = useState({ open: false, area: null })
  const [detailId, setDetailId] = useState(null)

  const ranking = useAsyncData(useCallback(() => areaRanking({}), []))

  const handleSubmit = useCallback(
    async (payload) => {
      if (formState.area) {
        await updateArea(formState.area.id, payload)
        toast.success(`片区 ${payload.name} 已更新`)
      } else {
        await createArea(payload)
        toast.success(`片区 ${payload.name} 已创建`)
      }
      setFormState({ open: false, area: null })
      resetOptionCache()
      query.reload()
      ranking.reload().catch(() => {})
    },
    [formState.area, query, ranking, toast]
  )

  useEffect(() => {
    if (tab === 'areas') ranking.reload().catch(() => {})
  }, [tab]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <div className="tabs">
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`tab ${tab === item.key ? 'active' : ''}`}
            onClick={() => setTab(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === 'persons' ? (
        <PersonsPanel />
      ) : (
        <>
          <AreaFilters
            value={query.filters}
            loading={query.loading}
            onSubmit={(next) => query.setFilters(next)}
            onReset={() => query.setFilters(INITIAL_FILTERS)}
          />

          {query.error ? <Alert tone="error">{query.error.message}</Alert> : null}

          <AreaRankingPanel data={ranking.data} loading={ranking.loading} />

          <SectionCard
            title="片区清单"
            hint="片区下挂多个监测点与责任人; 归属变动保留历史, 数据可按历史片区汇总"
            actions={
              <button type="button" className="btn btn-primary" onClick={() => setFormState({ open: true, area: null })}>
                + 新增片区
              </button>
            }
          >
            <AreaTable
              rows={query.items}
              loading={query.loading}
              onDetail={(row) => setDetailId(row.id)}
              onEdit={(row) => setFormState({ open: true, area: row })}
            />
            <Pagination
              page={query.page}
              pages={query.pages}
              total={query.total}
              pageSize={query.pageSize}
              onPageChange={query.setPage}
              onPageSizeChange={query.setPageSize}
            />
          </SectionCard>

          <AreaFormModal
            open={formState.open}
            area={formState.area}
            onClose={() => setFormState({ open: false, area: null })}
            onSubmit={handleSubmit}
          />

          <AreaDetailDrawer
            areaId={detailId}
            onClose={() => setDetailId(null)}
            onEdit={(area) => {
              setDetailId(null)
              setFormState({ open: true, area })
            }}
            onChanged={() => {
              query.reload()
              ranking.reload().catch(() => {})
            }}
          />
        </>
      )}
    </>
  )
}
