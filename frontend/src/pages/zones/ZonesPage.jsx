import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  addZoneManager,
  changeZoneManagerRole,
  createPerson,
  createZone,
  deletePerson,
  deleteZone,
  listPersons,
  listZones,
  removeZoneManager,
  updatePerson,
  updateZone
} from '../../api/zones.js'
import ConfirmDialog from '../../components/common/ConfirmDialog.jsx'
import Pagination from '../../components/common/Pagination.jsx'
import { SectionCard, FilterPanel } from '../../components/common/Card.jsx'
import { Field, Input, Select } from '../../components/common/FormField.jsx'
import { Alert } from '../../components/common/Feedback.jsx'
import { useToast } from '../../components/common/ToastProvider.jsx'
import { useListQuery } from '../../hooks/useListQuery.js'
import { resetOptionCache, useZoneOptions } from '../../hooks/useOptions.js'
import PersonFormModal from './components/PersonFormModal.jsx'
import PersonTable from './components/PersonTable.jsx'
import ManagerAssignModal from './components/ManagerAssignModal.jsx'
import ZoneDetailDrawer from './components/ZoneDetailDrawer.jsx'
import ZoneFormModal from './components/ZoneFormModal.jsx'
import ZoneTable from './components/ZoneTable.jsx'

const ZONE_INITIAL = { keyword: '', status: '' }
const PERSON_INITIAL = { keyword: '', status: '', zone_id: '' }

const ZONE_STATUS_OPTIONS = [
  { value: 'active', label: '启用' },
  { value: 'inactive', label: '停用' }
]

const PERSON_STATUS_OPTIONS = [
  { value: 'active', label: '在岗' },
  { value: 'inactive', label: '离岗' }
]

function ZoneFilters({ value, unassignedCount, loading, onSubmit, onReset }) {
  return (
    <FilterPanel
      loading={loading}
      onSearch={() => onSubmit(value)}
      onReset={() => onReset(ZONE_INITIAL)}
    >
      <Field label="关键字">
        <Input
          placeholder="片区名称 / 编码"
          value={value.keyword || ''}
          onChange={(event) => onSubmit({ ...value, keyword: event.target.value })}
          onKeyDown={(event) => event.key === 'Enter' && onSubmit(value)}
        />
      </Field>
      <Field label="片区状态">
        <Select
          value={value.status || ''}
          onChange={(event) => onSubmit({ ...value, status: event.target.value })}
          placeholder="全部状态"
          options={ZONE_STATUS_OPTIONS}
        />
      </Field>
      <Field label="未划分片区点位">
        <Link className="btn btn-sm" to="/stations?zone_id=none">
          {unassignedCount ?? 0} 个待处理 →
        </Link>
      </Field>
    </FilterPanel>
  )
}

function PersonFilters({ value, zoneOptions, loading, onSubmit, onReset }) {
  return (
    <FilterPanel
      loading={loading}
      onSearch={() => onSubmit(value)}
      onReset={() => onReset(PERSON_INITIAL)}
    >
      <Field label="关键字">
        <Input
          placeholder="姓名 / 工号 / 部门 / 电话"
          value={value.keyword || ''}
          onChange={(event) => onSubmit({ ...value, keyword: event.target.value })}
          onKeyDown={(event) => event.key === 'Enter' && onSubmit(value)}
        />
      </Field>
      <Field label="任职片区">
        <Select
          value={value.zone_id || ''}
          onChange={(event) => onSubmit({ ...value, zone_id: event.target.value })}
          placeholder="全部片区"
          options={(zoneOptions || []).map((zone) => ({ value: String(zone.id), label: zone.name }))}
        />
      </Field>
      <Field label="在岗状态">
        <Select
          value={value.status || ''}
          onChange={(event) => onSubmit({ ...value, status: event.target.value })}
          placeholder="全部状态"
          options={PERSON_STATUS_OPTIONS}
        />
      </Field>
    </FilterPanel>
  )
}

export default function ZonesPage() {
  const toast = useToast()
  const [tab, setTab] = useState('zones')
  const { data: zoneOptionsData } = useZoneOptions()

  const zoneQuery = useListQuery(listZones, ZONE_INITIAL)
  const personQuery = useListQuery(listPersons, PERSON_INITIAL)

  const [zoneForm, setZoneForm] = useState({ open: false, zone: null })
  const [personForm, setPersonForm] = useState({ open: false, person: null })
  const [detailId, setDetailId] = useState(null)
  const [managerModal, setManagerModal] = useState({ open: false, mode: 'add', zone: null, manager: null })
  const [pendingDeleteZone, setPendingDeleteZone] = useState(null)
  const [pendingDeletePerson, setPendingDeletePerson] = useState(null)
  const [busy, setBusy] = useState(false)

  const reloadAll = useCallback(() => {
    zoneQuery.reload()
    personQuery.reload()
    resetOptionCache()
  }, [zoneQuery, personQuery])

  // ---- 片区表单 ----
  const handleZoneSubmit = useCallback(
    async (payload) => {
      if (zoneForm.zone) {
        await updateZone(zoneForm.zone.id, payload)
        toast.success(`片区 ${payload.name} 已更新`)
      } else {
        await createZone(payload)
        toast.success(`片区 ${payload.name} 已创建`)
      }
      setZoneForm({ open: false, zone: null })
      reloadAll()
    },
    [zoneForm.zone, reloadAll, toast]
  )

  // ---- 责任人表单 ----
  const handlePersonSubmit = useCallback(
    async (payload) => {
      if (personForm.person) {
        await updatePerson(personForm.person.id, payload)
        toast.success(`责任人 ${payload.name} 已更新`)
      } else {
        await createPerson(payload)
        toast.success(`责任人 ${payload.name} 已创建`)
      }
      setPersonForm({ open: false, person: null })
      reloadAll()
    },
    [personForm.person, reloadAll, toast]
  )

  const handleDeleteZone = useCallback(async () => {
    if (!pendingDeleteZone) return
    setBusy(true)
    try {
      await deleteZone(pendingDeleteZone.id)
      toast.success(`片区 ${pendingDeleteZone.name} 已删除`)
      setPendingDeleteZone(null)
      reloadAll()
    } catch (error) {
      toast.error(error.message)
    } finally {
      setBusy(false)
    }
  }, [pendingDeleteZone, reloadAll, toast])

  const handleDeletePerson = useCallback(async () => {
    if (!pendingDeletePerson) return
    setBusy(true)
    try {
      await deletePerson(pendingDeletePerson.id)
      toast.success(`责任人 ${pendingDeletePerson.name} 已删除`)
      setPendingDeletePerson(null)
      reloadAll()
    } catch (error) {
      toast.error(error.message)
    } finally {
      setBusy(false)
    }
  }, [pendingDeletePerson, reloadAll, toast])

  // ---- 责任人任职变动 ----
  const refreshDetail = useCallback(() => {
    const current = detailId
    setDetailId(null)
    window.setTimeout(() => setDetailId(current), 0)
  }, [detailId])

  const handleManagerSubmit = useCallback(
    async (payload) => {
      if (managerModal.mode === 'role') {
        await changeZoneManagerRole(managerModal.zone.id, payload.person_id, payload)
        toast.success('角色已调整并记录历史')
      } else {
        await addZoneManager(managerModal.zone.id, payload)
        toast.success('责任人已分配到片区')
      }
      setManagerModal({ open: false, mode: 'add', zone: null, manager: null })
      resetOptionCache()
      zoneQuery.reload()
      refreshDetail()
    },
    [managerModal, zoneQuery, refreshDetail, toast]
  )

  const handleRemoveManager = useCallback(
    async (manager) => {
      const reason = window.prompt(`确认将 ${manager.person?.name} 移出该片区? 可填写变动说明(留空继续)`)
      if (reason === null) return
      try {
        await removeZoneManager(manager.zone_id, manager.person_id, { note: reason || null })
        toast.success('责任人已移除, 任职历史已保留')
        resetOptionCache()
        zoneQuery.reload()
        refreshDetail()
      } catch (error) {
        toast.error(error.message)
      }
    },
    [zoneQuery, refreshDetail, toast]
  )

  return (
    <>
      <div className="tabs">
        <button
          type="button"
          className={`tab ${tab === 'zones' ? 'active' : ''}`}
          onClick={() => setTab('zones')}
        >
          🗺️ 片区台账
        </button>
        <button
          type="button"
          className={`tab ${tab === 'persons' ? 'active' : ''}`}
          onClick={() => setTab('persons')}
        >
          👤 责任人台账
        </button>
      </div>

      {tab === 'zones' ? (
        <>
          <ZoneFilters
            value={zoneQuery.filters}
            unassignedCount={zoneQuery.data?.unassigned_station_count}
            loading={zoneQuery.loading}
            onSubmit={(next) => zoneQuery.setFilters(next)}
            onReset={(initial) => zoneQuery.setFilters(initial)}
          />
          {zoneQuery.error ? <Alert tone="error">{zoneQuery.error.message}</Alert> : null}
          <SectionCard
            title="片区清单"
            hint="片区下挂监测点与责任人; 待办与统计可按片区汇总并下钻"
            actions={
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setZoneForm({ open: true, zone: null })}
              >
                + 新增片区
              </button>
            }
          >
            <ZoneTable
              rows={zoneQuery.items}
              loading={zoneQuery.loading}
              onDetail={(row) => setDetailId(row.id)}
              onEdit={(row) => setZoneForm({ open: true, zone: row })}
              onDelete={(row) => setPendingDeleteZone(row)}
            />
            <Pagination
              page={zoneQuery.page}
              pages={zoneQuery.pages}
              total={zoneQuery.total}
              pageSize={zoneQuery.pageSize}
              onPageChange={zoneQuery.setPage}
              onPageSizeChange={zoneQuery.setPageSize}
            />
          </SectionCard>
        </>
      ) : (
        <>
          <PersonFilters
            value={personQuery.filters}
            zoneOptions={zoneOptionsData?.items ?? []}
            loading={personQuery.loading}
            onSubmit={(next) => personQuery.setFilters(next)}
            onReset={(initial) => personQuery.setFilters(initial)}
          />
          {personQuery.error ? <Alert tone="error">{personQuery.error.message}</Alert> : null}
          <SectionCard
            title="责任人清单"
            hint="责任人独立建档, 可在一个或多个片区任职; 离岗保留档案与历史"
            actions={
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setPersonForm({ open: true, person: null })}
              >
                + 新增责任人
              </button>
            }
          >
            <PersonTable
              rows={personQuery.items}
              loading={personQuery.loading}
              onEdit={(row) => setPersonForm({ open: true, person: row })}
              onDelete={(row) => setPendingDeletePerson(row)}
            />
            <Pagination
              page={personQuery.page}
              pages={personQuery.pages}
              total={personQuery.total}
              pageSize={personQuery.pageSize}
              onPageChange={personQuery.setPage}
              onPageSizeChange={personQuery.setPageSize}
            />
          </SectionCard>
        </>
      )}

      <ZoneFormModal
        open={zoneForm.open}
        zone={zoneForm.zone}
        onClose={() => setZoneForm({ open: false, zone: null })}
        onSubmit={handleZoneSubmit}
      />
      <PersonFormModal
        open={personForm.open}
        person={personForm.person}
        onClose={() => setPersonForm({ open: false, person: null })}
        onSubmit={handlePersonSubmit}
      />
      <ZoneDetailDrawer
        zoneId={detailId}
        onClose={() => setDetailId(null)}
        onEdit={(zone) => {
          setDetailId(null)
          setZoneForm({ open: true, zone })
        }}
        onAssignManager={(zone) =>
          setManagerModal({ open: true, mode: 'add', zone, manager: null })
        }
        onChangeRole={(manager, zone) =>
          setManagerModal({ open: true, mode: 'role', zone, manager })
        }
        onRemoveManager={handleRemoveManager}
      />
      <ManagerAssignModal
        open={managerModal.open}
        mode={managerModal.mode}
        zone={managerModal.zone}
        manager={managerModal.manager}
        onClose={() => setManagerModal({ open: false, mode: 'add', zone: null, manager: null })}
        onSubmit={handleManagerSubmit}
      />

      <ConfirmDialog
        open={Boolean(pendingDeleteZone)}
        danger
        busy={busy}
        title="删除片区"
        message={`确认删除片区「${pendingDeleteZone?.name || ''}」吗?`}
        detail="仅未使用且无历史记录的片区允许删除; 若已下挂点位请先调整归属, 或改为停用。"
        confirmText="确认删除"
        onConfirm={handleDeleteZone}
        onCancel={() => setPendingDeleteZone(null)}
      />
      <ConfirmDialog
        open={Boolean(pendingDeletePerson)}
        danger
        busy={busy}
        title="删除责任人"
        message={`确认删除责任人「${pendingDeletePerson?.name || ''}」吗?`}
        detail="存在任职记录或历史的责任人不允许删除, 建议将其状态改为离岗。"
        confirmText="确认删除"
        onConfirm={handleDeletePerson}
        onCancel={() => setPendingDeletePerson(null)}
      />
    </>
  )
}
