import { useNavigate } from 'react-router-dom'
import DataTable from '../../../components/common/DataTable.jsx'
import Tag from '../../../components/common/Tag.jsx'
import { ROLE_TONE, ZONE_STATUS_TONE } from '../../../constants/index.js'
import { formatNumber } from '../../../utils/format.js'

export default function ZoneTable({ rows, loading, onDetail, onEdit, onDelete }) {
  const navigate = useNavigate()

  const columns = [
    { key: 'code', title: '片区编码', className: 'mono cell-nowrap' },
    {
      key: 'name',
      title: '片区名称',
      render: (row) => (
        <div>
          <div className="strong">{row.name}</div>
          <div className="small muted">{row.description || '暂无说明'}</div>
        </div>
      )
    },
    {
      key: 'managers',
      title: '责任人',
      render: (row) => {
        const managers = row.stats?.managers || []
        if (!managers.length) return <span className="muted">未配置</span>
        return (
          <div className="stack" style={{ gap: 2 }}>
            {managers.slice(0, 2).map((person) => (
              <Tag key={person.id} tone={ROLE_TONE[person.role] || 'neutral'}>
                {person.name} · {person.role_label}
              </Tag>
            ))}
            {managers.length > 2 ? <span className="small muted">等 {managers.length} 人</span> : null}
          </div>
        )
      }
    },
    {
      key: 'station_count',
      title: '点位数',
      align: 'right',
      render: (row) => formatNumber(row.stats?.station_count ?? 0, 0)
    },
    {
      key: 'exceeded_count',
      title: '超标记录',
      align: 'right',
      render: (row) =>
        row.stats?.exceeded_count ? (
          <span className="danger-text strong">{row.stats.exceeded_count}</span>
        ) : (
          <span className="muted">0</span>
        )
    },
    {
      key: 'pending_count',
      title: '待标注待办',
      align: 'right',
      render: (row) =>
        row.stats?.pending_count ? (
          <Tag tone="warning">{row.stats.pending_count} 条</Tag>
        ) : (
          <span className="muted">-</span>
        )
    },
    {
      key: 'status',
      title: '状态',
      render: (row) => <Tag tone={ZONE_STATUS_TONE[row.status]}>{row.status_label}</Tag>
    },
    {
      key: 'actions',
      title: '操作',
      align: 'right',
      render: (row) => (
        <div className="btn-group">
          <button type="button" className="btn btn-sm" onClick={() => onDetail(row)}>
            详情
          </button>
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => navigate(`/exceedances?zone_id=${row.id}&status=pending`)}
          >
            待办
          </button>
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => navigate(`/query?zone_id=${row.id}`)}
          >
            下钻
          </button>
          <button type="button" className="btn btn-sm" onClick={() => onEdit(row)}>
            编辑
          </button>
          <button type="button" className="btn btn-sm btn-danger" onClick={() => onDelete(row)}>
            删除
          </button>
        </div>
      )
    }
  ]

  return (
    <DataTable
      columns={columns}
      rows={rows}
      loading={loading}
      onRowClick={onDetail}
      emptyText="还没有片区, 点击右上角“新增片区”开始划分管理网格"
      emptyIcon="🗺️"
    />
  )
}
