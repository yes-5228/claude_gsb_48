import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { batchAnnotate, listExceedances } from '../../api/exceedances.js'
import Pagination from '../../components/common/Pagination.jsx'
import { SectionCard } from '../../components/common/Card.jsx'
import { Alert } from '../../components/common/Feedback.jsx'
import Tag from '../../components/common/Tag.jsx'
import { useToast } from '../../components/common/ToastProvider.jsx'
import { useListQuery } from '../../hooks/useListQuery.js'
import { useUrlFilters } from '../../hooks/useUrlFilters.js'
import AnnotationModal from './components/AnnotationModal.jsx'
import ExceedanceFilters from './components/ExceedanceFilters.jsx'
import ExceedanceSummaryCards from './components/ExceedanceSummaryCards.jsx'
import ExceedanceTable from './components/ExceedanceTable.jsx'

const DEFAULT_FILTERS = {
  status: '',
  level: '',
  pollutant: '',
  station_id: '',
  zone_id: '',
  manager_id: '',
  date_from: '',
  date_to: '',
  keyword: ''
}

export default function ExceedancesPage() {
  const toast = useToast()
  const initialFilters = useUrlFilters(DEFAULT_FILTERS)
  const query = useListQuery(listExceedances, initialFilters)
  const [selected, setSelected] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [batch, setBatch] = useState({ status: 'confirmed', note: '', annotator: '' })
  const [busy, setBusy] = useState(false)

  const { reload } = query

  const toggleRow = useCallback((id) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]))
  }, [])

  const toggleAll = useCallback(
    (ids) => {
      setSelected((prev) => (ids.every((id) => prev.includes(id)) ? prev.filter((id) => !ids.includes(id)) : Array.from(new Set([...prev, ...ids]))))
    },
    []
  )

  const submitBatch = async () => {
    if (selected.length === 0) {
      toast.warning('请先勾选需要标注的超标记录')
      return
    }
    setBusy(true)
    try {
      const result = await batchAnnotate({
        ids: selected,
        status: batch.status,
        note: batch.note || null,
        annotator: batch.annotator || null
      })
      toast.success(`已标注 ${result.updated} 条记录`)
      if (result.missing?.length) toast.warning(`有 ${result.missing.length} 条记录不存在, 已跳过`)
      setSelected([])
      setBatch((prev) => ({ ...prev, note: '' }))
      reload()
    } catch (error) {
      toast.error(error.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <ExceedanceSummaryCards summary={query.summary} />

      {query.summary?.top_zones?.length ? (
        <SectionCard title="片区超标待办排名" hint="按当前筛选条件统计, 点击可下钻到该片区的待办超标记录">
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>排名</th>
                  <th>片区</th>
                  <th className="text-right">超标总数</th>
                  <th className="text-right">待标注</th>
                  <th>下钻</th>
                </tr>
              </thead>
              <tbody>
                {query.summary.top_zones.map((item, index) => (
                  <tr key={item.zone_id ?? 'none'}>
                    <td className="strong">{index + 1}</td>
                    <td className="strong">{item.zone_name}</td>
                    <td className="text-right">{item.count}</td>
                    <td className="text-right">
                      {item.pending_count ? (
                        <Tag tone="warning">{item.pending_count} 条待办</Tag>
                      ) : (
                        <span className="muted">0</span>
                      )}
                    </td>
                    <td>
                      <Link
                        className="btn btn-sm"
                        to={`/exceedances?status=pending&zone_id=${item.zone_id ?? 'none'}`}
                      >
                        查看待办
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      ) : null}

      <ExceedanceFilters
        value={query.filters}
        loading={query.loading}
        onSubmit={(next) => {
          setSelected([])
          query.setFilters(next)
        }}
        onReset={() => {
          setSelected([])
          query.setFilters(DEFAULT_FILTERS)
        }}
      />

      {query.error ? <Alert tone="error">{query.error.message}</Alert> : null}

      <SectionCard
        title="超标记录工作台"
        hint="点击行可打开单条标注; 勾选多条后可批量确认或忽略"
        actions={
          <>
            <Tag tone="primary">已选 {selected.length} 条</Tag>
            <button type="button" className="btn btn-sm" onClick={reload} disabled={query.loading}>
              刷新
            </button>
          </>
        }
      >
        <div className="stack">
          <div className="card" style={{ boxShadow: 'none' }}>
            <div className="card-body tight">
              <div className="inline">
                <span className="field-label">批量标注</span>
                <select
                  className="select"
                  style={{ width: 150 }}
                  value={batch.status}
                  onChange={(event) => setBatch({ ...batch, status: event.target.value })}
                >
                  <option value="confirmed">已确认</option>
                  <option value="ignored">已忽略</option>
                  <option value="pending">重置为待标注</option>
                </select>
                <input
                  className="input"
                  style={{ flex: 1, minWidth: 220 }}
                  placeholder="标注说明 (确认或忽略时必填)"
                  value={batch.note}
                  onChange={(event) => setBatch({ ...batch, note: event.target.value })}
                />
                <input
                  className="input"
                  style={{ width: 140 }}
                  placeholder="标注人"
                  value={batch.annotator}
                  onChange={(event) => setBatch({ ...batch, annotator: event.target.value })}
                />
                <button type="button" className="btn btn-primary" onClick={submitBatch} disabled={busy}>
                  {busy ? '提交中...' : '提交批量标注'}
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => setSelected([])}
                  disabled={selected.length === 0}
                >
                  清空选择
                </button>
              </div>
            </div>
          </div>

          <ExceedanceTable
            rows={query.items}
            loading={query.loading}
            selectedIds={selected}
            onToggleRow={toggleRow}
            onToggleAll={toggleAll}
            onOpen={(row) => setActiveId(row.id)}
          />
          <Pagination
            page={query.page}
            pages={query.pages}
            total={query.total}
            pageSize={query.pageSize}
            onPageChange={query.setPage}
            onPageSizeChange={query.setPageSize}
          />
        </div>
      </SectionCard>

      <AnnotationModal
        exceedanceId={activeId}
        onClose={() => setActiveId(null)}
        onSaved={() => {
          setActiveId(null)
          reload()
        }}
      />
    </>
  )
}
