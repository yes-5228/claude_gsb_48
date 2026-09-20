import DataTable from '../../../components/common/DataTable.jsx'
import Tag from '../../../components/common/Tag.jsx'
import { formatNumber, formatPercent } from '../../../utils/format.js'

export default function AreaTable({ rows, loading, onDetail, onEdit }) {
  const columns = [
    { key: 'code', title: '片区编码', className: 'mono cell-nowrap' },
    {
      key: 'name',
      title: '片区名称',
      render: (row) => (
        <div>
          <div className="strong">{row.name}</div>
          <div className="small muted">
            {row.manager ? `主管: ${row.manager}` : '未设置主管'}
            {row.phone ? ` · ${row.phone}` : ''}
          </div>
        </div>
      )
    },
    {
      key: 'persons',
      title: '责任人',
      render: (row) =>
        row.persons?.length ? (
          <div className="inline" style={{ gap: 4, flexWrap: 'wrap' }}>
            {row.persons.map((person) => (
              <Tag key={person.person_id} tone="primary" title={person.role_label}>
                {person.name}
              </Tag>
            ))}
          </div>
        ) : (
          <span className="muted">未配置</span>
        )
    },
    {
      key: 'status',
      title: '状态',
      className: 'cell-nowrap',
      render: (row) => <Tag tone={row.status === 'active' ? 'success' : 'neutral'}>{row.status_label}</Tag>
    },
    {
      key: 'station_count',
      title: '点位数',
      align: 'right',
      render: (row) => formatNumber(row.stats?.station_count ?? 0, 0)
    },
    {
      key: 'measurement_count',
      title: '监测数据',
      align: 'right',
      render: (row) => formatNumber(row.stats?.measurement_count ?? 0, 0)
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
      title: '待办超标',
      align: 'right',
      render: (row) =>
        row.stats?.pending_count ? (
          <Tag tone="warning">{row.stats.pending_count} 条</Tag>
        ) : (
          <span className="muted">-</span>
        )
    },
    {
      key: 'exceed_rate',
      title: '超标率',
      align: 'right',
      render: (row) => {
        const total = row.stats?.measurement_count || 0
        const exceeded = row.stats?.exceeded_count || 0
        return total ? formatPercent(exceeded / total) : '-'
      }
    },
    {
      key: 'actions',
      title: '操作',
      align: 'right',
      render: (row) => (
        <div className="btn-group">
          <button type="button" className="btn btn-sm" onClick={() => onDetail(row)}>
            详情/下钻
          </button>
          <button type="button" className="btn btn-sm" onClick={() => onEdit(row)}>
            编辑
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
      emptyText="还没有片区, 点击右上角“新增片区”开始管理"
      emptyIcon="🗺️"
    />
  )
}
