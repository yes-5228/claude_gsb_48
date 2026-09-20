import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  addMembership,
  assignStations,
  getArea,
  leaveMembership,
  listPersons,
  membershipHistory
} from '../../../api/areas.js'
import { stationOptions } from '../../../api/stations.js'
import Modal from '../../../components/common/Modal.jsx'
import Tag from '../../../components/common/Tag.jsx'
import DataTable from '../../../components/common/DataTable.jsx'
import { Alert } from '../../../components/common/Feedback.jsx'
import { useAsyncData } from '../../../hooks/useAsyncData.js'
import { resetOptionCache } from '../../../hooks/useOptions.js'
import { formatDateTime, formatNumber } from '../../../utils/format.js'
import AssignStationsModal from './AssignStationsModal.jsx'
import LeaveMembershipModal from './LeaveMembershipModal.jsx'
import MembershipModal from './MembershipModal.jsx'

const TABS = [
  { key: 'stations', label: '下辖点位' },
  { key: 'persons', label: '责任人' },
  { key: 'history', label: '归属变更历史' }
]

export default function AreaDetailDrawer({ areaId, onClose, onEdit, onChanged }) {
  const [tab, setTab] = useState('stations')
  const [assignOpen, setAssignOpen] = useState(false)
  const [memberOpen, setMemberOpen] = useState(false)
  const [leaveTarget, setLeaveTarget] = useState(null)
  const [error, setError] = useState(null)

  const loader = useCallback(() => (areaId ? getArea(areaId) : Promise.resolve(null)), [areaId])
  const { data, loading, error: loadError, reload } = useAsyncData(loader, {
    immediate: Boolean(areaId)
  })

  const allStations = useAsyncData(
    useCallback(() => (areaId ? stationOptions() : Promise.resolve(null)), [areaId]),
    { immediate: Boolean(areaId) }
  )
  // 可添加的责任人 = 全部责任人中当前不在本片区任职的人
  const allPersons = useAsyncData(
    useCallback(async () => {
      const result = await listPersons({ page_size: 200 })
      const currentIds = new Set((data?.persons || []).map((item) => item.person_id))
      return result.items.filter((item) => !currentIds.has(item.id))
    }, [data]),
    { immediate: Boolean(areaId) && memberOpen }
  )
  const historyData = useAsyncData(
    useCallback(() => (areaId ? membershipHistory({ area_id: areaId, limit: 100 }) : Promise.resolve(null)), [areaId]),
    { immediate: false }
  )

  const open = Boolean(areaId)
  const area = data?.area
  const stats = data?.stats || {}

  const refresh = () => {
    reload().catch(() => {})
    resetOptionCache()
    onChanged?.()
  }

  const handleAssign = async (payload) => {
    await assignStations(payload)
    setAssignOpen(false)
    refresh()
  }

  const handleAddMembership = async (payload) => {
    await addMembership(payload)
    setMemberOpen(false)
    refresh()
  }

  const handleLeave = async ({ change_reason, changed_by }) => {
    await leaveMembership(leaveTarget.membership_id, { change_reason, changed_by })
    setLeaveTarget(null)
    refresh()
  }

  const stationColumns = [
    { key: 'code', title: '监测点编码', className: 'mono' },
    { key: 'name', title: '监测点名称' },
    { key: 'station_type_label', title: '类型' },
    {
      key: 'status',
      title: '状态',
      render: (row) => (
        <Tag tone={row.status === 'active' ? 'success' : row.status === 'maintenance' ? 'warning' : 'neutral'}>
          {row.status_label}
        </Tag>
      )
    },
    {
      key: 'actions',
      title: '操作',
      align: 'right',
      render: (row) => (
        <Link className="btn btn-sm" to={`/query?area_id=${areaId}`}>
          查询该点位数据
        </Link>
      )
    }
  ]

  const personColumns = [
    { key: 'name', title: '姓名', render: (row) => <span className="strong">{row.name}</span> },
    { key: 'employee_no', title: '工号', className: 'mono', render: (row) => row.employee_no || '-' },
    { key: 'role_label', title: '片区岗位' },
    { key: 'phone', title: '电话', render: (row) => row.phone || '-' },
    { key: 'department', title: '部门', render: (row) => row.department || '-' },
    {
      key: 'actions',
      title: '操作',
      align: 'right',
      render: (row) => (
        <button
          type="button"
          className="btn btn-sm btn-danger"
          onClick={() => setLeaveTarget({ membership_id: row.membership_id, name: row.name })}
        >
          办理卸任
        </button>
      )
    }
  ]

  const historyColumns = [
    { key: 'person_name', title: '责任人' },
    { key: 'role_label', title: '岗位' },
    {
      key: 'effective_from',
      title: '任职开始',
      render: (row) => formatDateTime(row.effective_from)
    },
    {
      key: 'effective_end',
      title: '任职结束',
      render: (row) => (row.effective_end ? formatDateTime(row.effective_end) : <Tag tone="success">在任</Tag>)
    },
    { key: 'change_reason', title: '变更原因', render: (row) => row.change_reason || '-' },
    { key: 'changed_by', title: '操作人', render: (row) => row.changed_by || '-' }
  ]

  return (
    <Modal
      open={open}
      drawer
      title="片区详情"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            关闭
          </button>
          {area ? (
            <button type="button" className="btn btn-primary" onClick={() => onEdit(area)}>
              编辑片区
            </button>
          ) : null}
        </>
      }
    >
      {loading && !data ? (
        <div className="loading">加载中...</div>
      ) : loadError && !data ? (
        <Alert tone="error">{loadError.message}</Alert>
      ) : area ? (
        <div className="stack">
          <div className="inline">
            <h3 style={{ margin: 0 }}>{area.name}</h3>
            <Tag tone="primary">{area.code}</Tag>
            <Tag tone={area.status === 'active' ? 'success' : 'neutral'}>{area.status_label}</Tag>
          </div>
          <dl className="kv">
            <dt>片区主管</dt>
            <dd>{area.manager || '-'}</dd>
            <dt>联系电话</dt>
            <dd>{area.phone || '-'}</dd>
            <dt>备注</dt>
            <dd>{area.remark || '-'}</dd>
          </dl>
          <div className="stat-grid">
            <div className="stat-card">
              <div className="stat-label">下辖点位</div>
              <div className="stat-value">{stats.station_count ?? 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">监测数据</div>
              <div className="stat-value">{formatNumber(stats.measurement_count ?? 0, 0)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">超标记录</div>
              <div className="stat-value danger-text">{stats.exceeded_count ?? 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">待办超标</div>
              <div className="stat-value" style={{ color: 'var(--warning)' }}>
                {stats.pending_count ?? 0}
              </div>
            </div>
          </div>

          <div className="tabs">
            {TABS.map((item) => (
              <button
                key={item.key}
                type="button"
                className={`tab ${tab === item.key ? 'active' : ''}`}
                onClick={() => {
                  setTab(item.key)
                  if (item.key === 'history') historyData.reload().catch(() => {})
                }}
              >
                {item.label}
              </button>
            ))}
          </div>

          {error ? <Alert tone="error">{error}</Alert> : null}

          {tab === 'stations' ? (
            <div className="stack">
              <div className="inline">
                <Link className="btn btn-sm" to={`/query?area_id=${areaId}`}>
                  查询片区数据
                </Link>
                <Link className="btn btn-sm" to={`/exceedances?area_id=${areaId}`}>
                  查看片区超标待办
                </Link>
                <button type="button" className="btn btn-sm btn-primary" onClick={() => setAssignOpen(true)}>
                  划转监测点到本片区
                </button>
              </div>
              <DataTable columns={stationColumns} rows={data.stations || []} emptyText="该片区暂无监测点" />
            </div>
          ) : null}

          {tab === 'persons' ? (
            <div className="stack">
              <div className="inline">
                <button type="button" className="btn btn-sm btn-primary" onClick={() => setMemberOpen(true)}>
                  添加责任人
                </button>
                <span className="hint">责任人变动(卸任/轮岗)会以时间分段方式保留任职历史</span>
              </div>
              <DataTable columns={personColumns} rows={data.persons || []} emptyText="该片区暂无责任人" />
            </div>
          ) : null}

          {tab === 'history' ? (
            <DataTable
              columns={historyColumns}
              rows={historyData.data?.items || []}
              loading={historyData.loading}
              emptyText="暂无责任人变更记录"
            />
          ) : null}
        </div>
      ) : null}

      {area && allStations.data ? (
        <AssignStationsModal
          open={assignOpen}
          area={area}
          stations={allStations.data.items || []}
          onClose={() => setAssignOpen(false)}
          onSubmit={handleAssign}
        />
      ) : null}

      {area ? (
        <MembershipModal
          open={memberOpen}
          area={area}
          persons={allPersons.data || []}
          onClose={() => setMemberOpen(false)}
          onSubmit={handleAddMembership}
        />
      ) : null}

      <LeaveMembershipModal
        open={Boolean(leaveTarget)}
        payload={leaveTarget}
        onClose={() => setLeaveTarget(null)}
        onSubmit={handleLeave}
      />
    </Modal>
  )
}
