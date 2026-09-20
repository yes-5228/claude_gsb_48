import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getZone } from '../../../api/zones.js'
import Modal from '../../../components/common/Modal.jsx'
import Tag from '../../../components/common/Tag.jsx'
import DataTable from '../../../components/common/DataTable.jsx'
import { ErrorState, Loading } from '../../../components/common/Feedback.jsx'
import { ROLE_TONE, ZONE_STATUS_TONE } from '../../../constants/index.js'
import { useAsyncData } from '../../../hooks/useAsyncData.js'
import { formatDateTime, formatNumber } from '../../../utils/format.js'

export default function ZoneDetailDrawer({ zoneId, onClose, onEdit, onAssignManager, onChangeRole, onRemoveManager }) {
  const navigate = useNavigate()
  const loader = useCallback(() => getZone(zoneId), [zoneId])
  const { data, loading, error } = useAsyncData(loader, { immediate: Boolean(zoneId) })

  const open = Boolean(zoneId)
  const stationColumns = [
    { key: 'code', title: '监测点编码', className: 'mono cell-nowrap' },
    { key: 'name', title: '监测点名称' },
    { key: 'area', title: '行政区域', className: 'cell-nowrap' },
    {
      key: 'pending_count',
      title: '待标注',
      align: 'right',
      render: (row) =>
        row.stats?.pending_count ? <Tag tone="warning">{row.stats.pending_count}</Tag> : <span className="muted">-</span>
    },
    {
      key: 'actions',
      title: '下钻',
      align: 'right',
      render: (row) => (
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => navigate(`/query?zone_id=${data.zone.id}&station_id=${row.id}`)}
        >
          查询数据
        </button>
      )
    }
  ]

  const managerColumns = [
    { key: 'name', title: '责任人', render: (row) => row.person?.name || '-' },
    { key: 'employee_no', title: '工号', render: (row) => row.person?.employee_no || '-' },
    { key: 'phone', title: '电话', render: (row) => row.person?.phone || '-' },
    {
      key: 'role',
      title: '角色',
      render: (row) => <Tag tone={ROLE_TONE[row.role]}>{row.role_label}</Tag>
    },
    {
      key: 'status',
      title: '状态',
      render: (row) => (
        <Tag tone={row.person?.status === 'active' ? 'success' : 'neutral'}>
          {row.person?.status === 'active' ? '在岗' : '离岗'}
        </Tag>
      )
    },
    {
      key: 'actions',
      title: '操作',
      align: 'right',
      render: (row) => (
        <div className="btn-group">
          <button type="button" className="btn btn-sm" onClick={() => onChangeRole(row, data.zone)}>
            调整角色
          </button>
          <button type="button" className="btn btn-sm btn-danger" onClick={() => onRemoveManager(row)}>
            移除
          </button>
        </div>
      )
    }
  ]

  const historyColumns = [
    {
      key: 'changed_at',
      title: '时间',
      className: 'cell-nowrap',
      render: (row) => formatDateTime(row.changed_at)
    },
    {
      key: 'type',
      title: '类型',
      render: (row) => <Tag tone="info">{row.reason_label || row.change_type_label}</Tag>
    },
    {
      key: 'detail',
      title: '变动内容',
      render: (row) =>
        row.station_name ? (
          <span>
            <span className="strong">{row.station_name}</span>
            <span className="muted">
              {' '}
              {row.previous_zone_name ? `${row.previous_zone_name} → ` : ''}
              {row.zone_name || '未划分片区'}
            </span>
          </span>
        ) : (
          <span>
            <span className="strong">{row.person_name}</span>
            <span className="muted">
              {' '}
              {row.previous_role_label ? `${row.previous_role_label} → ${row.role_label}` : row.change_type_label}
            </span>
          </span>
        )
    },
    { key: 'operator', title: '操作人', render: (row) => row.operator || '-' },
    { key: 'note', title: '说明', render: (row) => row.note || '-' }
  ]

  const historyItems = [
    ...(data?.station_history || []).map((item) => ({ ...item, _kind: 'station' })),
    ...(data?.manager_history || []).map((item) => ({ ...item, _kind: 'manager' }))
  ].sort((a, b) => (a.changed_at < b.changed_at ? 1 : -1))

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
          {data ? (
            <>
              <button type="button" className="btn" onClick={() => onAssignManager(data.zone)}>
                分配责任人
              </button>
              <button type="button" className="btn btn-primary" onClick={() => onEdit(data.zone)}>
                编辑片区
              </button>
            </>
          ) : null}
        </>
      }
    >
      {loading && !data ? <Loading /> : null}
      {error && !data ? <ErrorState error={error} /> : null}
      {data ? (
        <div className="stack">
          <div className="inline">
            <h3 style={{ margin: 0 }}>{data.zone.name}</h3>
            <Tag tone={ZONE_STATUS_TONE[data.zone.status]}>{data.zone.status_label}</Tag>
            <span className="mono muted small">{data.zone.code}</span>
          </div>
          <p className="muted small" style={{ margin: 0 }}>
            {data.zone.description || '暂无片区说明'}
          </p>

          <div className="stat-grid">
            <div className="stat-card">
              <div className="stat-label">下辖点位</div>
              <div className="stat-value">{data.stats.station_count ?? 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">监测数据量</div>
              <div className="stat-value">{formatNumber(data.stats.measurement_count ?? 0, 0)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">超标记录</div>
              <div className="stat-value danger-text">{data.stats.exceeded_count ?? 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">待标注</div>
              <div className="stat-value" style={{ color: 'var(--warning)' }}>
                {data.stats.pending_count ?? 0}
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h3>片区责任人 ({data.zone.managers?.length || 0})</h3>
            </div>
            <DataTable
              columns={managerColumns}
              rows={data.zone.managers || []}
              emptyText="尚未分配责任人, 点击底部“分配责任人”"
              emptyIcon="👤"
            />
          </div>

          <div className="card">
            <div className="card-header">
              <h3>下辖监测点</h3>
              <span className="hint">归属调整请在监测点台账中操作</span>
            </div>
            <DataTable columns={stationColumns} rows={data.stations || []} emptyText="该片区下暂无监测点" emptyIcon="📍" />
          </div>

          <div className="card">
            <div className="card-header">
              <h3>变更历史</h3>
              <span className="hint">归属与任职变动均不可修改, 长期保留</span>
            </div>
            <DataTable
              columns={historyColumns}
              rows={historyItems}
              rowKey={(row) => `${row._kind}-${row.id}`}
              emptyText="暂无变更记录"
              emptyIcon="🧾"
            />
          </div>
        </div>
      ) : null}
    </Modal>
  )
}
