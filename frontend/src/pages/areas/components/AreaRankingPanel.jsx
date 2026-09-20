import { Link } from 'react-router-dom'
import { SectionCard } from '../../../components/common/Card.jsx'
import BarChart from '../../../components/common/BarChart.jsx'
import DataTable from '../../../components/common/DataTable.jsx'
import Tag from '../../../components/common/Tag.jsx'
import { formatNumber, formatPercent } from '../../../utils/format.js'

/** 片区统计排名: 数据量 / 超标 / 超标率 / 待办待标注, 支持点击下钻到待办。 */
export default function AreaRankingPanel({ data, loading }) {
  const items = (data?.items || []).map((item) => ({
    key: item.area_id ?? item.key,
    label: item.label,
    value: item.exceeded_count,
    exceeded_count: item.exceeded_count
  }))

  const columns = [
    {
      key: 'rank',
      title: '排名',
      width: 60,
      render: (row) => {
        const index = data.items.findIndex((item) => item.area_id === row.area_id) + 1
        const tone = index <= 3 ? 'danger' : 'neutral'
        return <Tag tone={tone}>第 {index} 名</Tag>
      }
    },
    { key: 'label', title: '片区', render: (row) => <span className="strong">{row.label}</span> },
    { key: 'measurement_count', title: '监测数据量', align: 'right', render: (row) => formatNumber(row.measurement_count, 0) },
    {
      key: 'exceeded_count',
      title: '超标记录',
      align: 'right',
      render: (row) => (row.exceeded_count ? <span className="danger-text strong">{row.exceeded_count}</span> : '0')
    },
    { key: 'exceed_rate', title: '超标率', align: 'right', render: (row) => formatPercent(row.exceed_rate) },
    {
      key: 'pending_count',
      title: '待办待标注',
      align: 'right',
      render: (row) => (row.pending_count ? <Tag tone="warning">{row.pending_count} 条</Tag> : <span className="muted">-</span>)
    },
    {
      key: 'actions',
      title: '下钻',
      align: 'right',
      render: (row) => (
        <div className="btn-group">
          <Link className="btn btn-sm" to={`/query?area_id=${row.area_id ?? ''}`}>
            数据查询
          </Link>
          <Link className="btn btn-sm" to={`/exceedances?area_id=${row.area_id ?? ''}`}>
            超标待办
          </Link>
        </div>
      )
    }
  ]

  return (
    <SectionCard
      title="片区统计排名"
      hint="按数据产生时监测点所属片区汇总 (历史归属); 排名按待办数、超标数、数据量降序"
    >
      <div className="stack">
        {items.length > 0 ? <BarChart items={items} precision={0} /> : <div className="empty">{loading ? '正在统计...' : '暂无统计数据'}</div>}
        <DataTable columns={columns} rows={data?.items || []} loading={loading} emptyText="暂无片区统计" />
        {data?.totals ? (
          <div className="hint">
            合计 {formatNumber(data.totals.measurement_count, 0)} 条监测数据 · 超标 {data.totals.exceeded_count} 条 · 待办 {data.totals.pending_count} 条
          </div>
        ) : null}
      </div>
    </SectionCard>
  )
}
