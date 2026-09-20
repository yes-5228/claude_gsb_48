import { useCallback, useState } from 'react'
import { assignStationsToZone, createStation, deleteStation, listStations, updateStation } from '../../api/stations.js'
import ConfirmDialog from '../../components/common/ConfirmDialog.jsx'
import Pagination from '../../components/common/Pagination.jsx'
import { SectionCard } from '../../components/common/Card.jsx'
import { Alert } from '../../components/common/Feedback.jsx'
import Tag from '../../components/common/Tag.jsx'
import { useToast } from '../../components/common/ToastProvider.jsx'
import { useListQuery } from '../../hooks/useListQuery.js'
import { resetOptionCache } from '../../hooks/useOptions.js'
import { useUrlFilters } from '../../hooks/useUrlFilters.js'
import BatchZoneAssignModal from './components/BatchZoneAssignModal.jsx'
import StationDetailDrawer from './components/StationDetailDrawer.jsx'
import StationFilters from './components/StationFilters.jsx'
import StationFormModal from './components/StationFormModal.jsx'
import StationTable from './components/StationTable.jsx'

const DEFAULT_FILTERS = { keyword: '', area: '', zone_id: '', status: '', station_type: '' }

export default function StationsPage() {
  const toast = useToast()
  const initialFilters = useUrlFilters(DEFAULT_FILTERS)
  const query = useListQuery(listStations, initialFilters)
  const [formState, setFormState] = useState({ open: false, station: null })
  const [detailId, setDetailId] = useState(null)
  const [pendingDelete, setPendingDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [selectedIds, setSelectedIds] = useState([])
  const [batchOpen, setBatchOpen] = useState(false)

  const { reload } = query
  const areas = query.data?.areas ?? []

  const handleSubmit = useCallback(
    async (payload) => {
      if (formState.station) {
        await updateStation(formState.station.id, payload)
        toast.success(`监测点 ${payload.code} 已更新`)
      } else {
        await createStation(payload)
        toast.success(`监测点 ${payload.code} 已创建`)
      }
      setFormState({ open: false, station: null })
      resetOptionCache() // 台账变更后刷新下拉选项缓存
      reload()
    },
    [formState.station, reload, toast]
  )

  const handleDelete = useCallback(async () => {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      const result = await deleteStation(pendingDelete.id)
      toast.success(
        `已删除 ${pendingDelete.code}, 同时清理监测数据 ${result.removed.measurements_removed} 条、超标记录 ${result.removed.exceedances_removed} 条`
      )
      setPendingDelete(null)
      resetOptionCache()
      reload()
    } catch (error) {
      toast.error(error.message)
    } finally {
      setDeleting(false)
    }
  }, [pendingDelete, reload, toast])

  const toggleRow = useCallback((id) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]))
  }, [])

  const toggleAll = useCallback((ids) => {
    setSelectedIds((prev) =>
      ids.every((id) => prev.includes(id)) ? prev.filter((id) => !ids.includes(id)) : Array.from(new Set([...prev, ...ids]))
    )
  }, [])

  const handleBatchAssign = useCallback(
    async (payload) => {
      const result = await assignStationsToZone(payload)
      toast.success(
        `批量归属完成: ${result.changed} 个点位已调整` +
          (result.unchanged ? `, ${result.unchanged} 个本就属于该片区` : '') +
          (result.missing?.length ? `, ${result.missing.length} 个未找到` : '')
      )
      setBatchOpen(false)
      setSelectedIds([])
      resetOptionCache()
      reload()
    },
    [reload, toast]
  )

  return (
    <>
      <StationFilters
        value={query.filters}
        areas={areas}
        zones={query.data?.zones ?? []}
        loading={query.loading}
        onSubmit={(next) => query.setFilters(next)}
        onReset={() => query.setFilters(DEFAULT_FILTERS)}
      />

      {query.error ? <Alert tone="error">{query.error.message}</Alert> : null}

      <SectionCard
        title="监测点清单"
        hint="台账信息用于数据录入与超标记录的归属追溯; 勾选多个点位可批量归属片区"
        actions={
          <>
            {selectedIds.length ? <Tag tone="primary">已选 {selectedIds.length} 个</Tag> : null}
            <button
              type="button"
              className="btn"
              disabled={selectedIds.length === 0}
              onClick={() => setBatchOpen(true)}
            >
              批量归属片区
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setFormState({ open: true, station: null })}
            >
              + 新增监测点
            </button>
          </>
        }
      >
        <StationTable
          rows={query.items}
          loading={query.loading}
          selectedIds={selectedIds}
          onToggleRow={toggleRow}
          onToggleAll={toggleAll}
          onDetail={(row) => setDetailId(row.id)}
          onEdit={(row) => setFormState({ open: true, station: row })}
          onDelete={(row) => setPendingDelete(row)}
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

      <BatchZoneAssignModal
        open={batchOpen}
        stationIds={selectedIds}
        onClose={() => setBatchOpen(false)}
        onSubmit={handleBatchAssign}
      />

      <StationFormModal
        open={formState.open}
        station={formState.station}
        areas={areas}
        onClose={() => setFormState({ open: false, station: null })}
        onSubmit={handleSubmit}
      />

      <StationDetailDrawer
        stationId={detailId}
        onClose={() => setDetailId(null)}
        onEdit={(station) => {
          setDetailId(null)
          setFormState({ open: true, station })
        }}
      />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        danger
        busy={deleting}
        title="删除监测点"
        message={`确认删除监测点「${pendingDelete?.name || ''}」吗?`}
        detail="删除后该监测点下的监测数据与超标记录将一并移除, 该操作不可恢复。"
        confirmText="确认删除"
        onConfirm={handleDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </>
  )
}
