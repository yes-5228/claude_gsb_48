import { useCallback } from 'react'
import { getStation } from '../../../api/stations.js'
import Modal from '../../../components/common/Modal.jsx'
import Tag from '../../../components/common/Tag.jsx'
import DataTable from '../../../components/common/DataTable.jsx'
import { ErrorState, Loading } from '../../../components/common/Feedback.jsx'
import { STATION_STATUS_TONE } from '../../../constants/index.js'
import { useAsyncData } from '../../../hooks/useAsyncData.js'
import { formatDate, formatDateTime, formatNumber } from '../../../utils/format.js'

export default function StationDetailDrawer({ stationId, onClose, onEdit }) {
  const loader = useCallback(() => getStation(stationId), [stationId])
  const { data, loading, error } = useAsyncData(loader, { immediate: Boolean(stationId) })

  const open = Boolean(stationId)
  const stats = data?.stats || {}

  const columns = [
    { key: 'pollutant', title: '监测因子' },
    { key: 'count', title: '数据量', align: 'right' },
    { key: 'exceeded_count', title: '超标', align: 'right', render: (row) => (row.exceeded_count ? <span className="danger-text">{row.exceeded_count}</span> : '0') },
    { key: 'avg_value', title: '均值', align: 'right', render: (row) => formatNumber(row.avg_value) },
    { key: 'max_value', title: '最大值', align: 'right', render: (row) => formatNumber(row.max_value) }
  ]

  const assignmentColumns = [
    { key: 'area_name', title: '所属片区', render: (row) => <span className="strong">{row.area_name}</span> },
    {
      key: 'effective_from',
      title: '生效开始',
      render: (row) => formatDateTime(row.effective_from)
    },
    {
      key: 'effective_end',
      title: '生效结束',
      render: (row) =>
        row.is_current ? <Tag tone="success">当前归属</Tag> : formatDateTime(row.effective_end)
    },
    { key: 'change_reason', title: '变更原因', render: (row) => row.change_reason || '-' },
    { key: 'changed_by', title: '操作人', render: (row) => row.changed_by || '-' }
  ]

  return (
    <Modal
      open={open}
      drawer
      title="监测点详情"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            关闭
          </button>
          {data ? (
            <button type="button" className="btn btn-primary" onClick={() => onEdit(data)}>
              编辑台账
            </button>
          ) : null}
        </>
      }
    >
      {loading && !data ? <Loading /> : null}
      {error && !data ? <ErrorState error={error} /> : null}
      {data ? (
        <div className="stack">
          <div className="inline">
            <h3 style={{ margin: 0 }}>{data.name}</h3>
            <Tag tone={STATION_STATUS_TONE[data.status]}>{data.status_label}</Tag>
            <Tag tone="primary">{data.station_type_label}</Tag>
          </div>
          <dl className="kv">
            <dt>监测点编码</dt>
            <dd className="mono">{data.code}</dd>
            <dt>所属片区</dt>
            <dd>{data.area || '-'}</dd>
            <dt>详细地址</dt>
            <dd>{data.address || '-'}</dd>
            <dt>经纬度</dt>
            <dd>
              {data.longitude !== null && data.latitude !== null
                ? `${data.longitude}, ${data.latitude}`
                : '-'}
            </dd>
            <dt>投运日期</dt>
            <dd>{formatDate(data.installed_at)}</dd>
            <dt>最近上报</dt>
            <dd>{formatDateTime(stats.last_measured_at)}</dd>
            <dt>备注</dt>
            <dd>{data.remark || '-'}</dd>
          </dl>
          <div className="stat-grid">
            <div className="stat-card">
              <div className="stat-label">累计监测数据</div>
              <div className="stat-value">{stats.measurement_count ?? 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">超标记录</div>
              <div className="stat-value danger-text">{stats.exceeded_count ?? 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">待标注</div>
              <div className="stat-value" style={{ color: 'var(--warning)' }}>
                {stats.pending_count ?? 0}
              </div>
            </div>
          </div>
          <div className="card">
            <div className="card-header">
              <h3>按因子统计</h3>
              <span className="hint">限值参考 GB 3095-2012 二级标准</span>
            </div>
            <DataTable columns={columns} rows={stats.pollutants || []} emptyText="该监测点暂无监测数据" />
          </div>

          <div className="card">
            <div className="card-header">
              <h3>片区归属历史</h3>
              <span className="hint">归属或责任人变动后, 历史数据按当时片区汇总</span>
            </div>
            <DataTable
              columns={assignmentColumns}
              rows={data.assignments || []}
              emptyText="暂无归属记录"
            />
          </div>
        </div>
      ) : null}
    </Modal>
  )
}
