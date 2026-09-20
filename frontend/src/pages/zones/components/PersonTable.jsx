import { useNavigate } from 'react-router-dom'
import DataTable from '../../../components/common/DataTable.jsx'
import Tag from '../../../components/common/Tag.jsx'
import { PERSON_STATUS_TONE, ROLE_TONE } from '../../../constants/index.js'

export default function PersonTable({ rows, loading, onEdit, onDelete }) {
  const navigate = useNavigate()

  const columns = [
    { key: 'name', title: '姓名', className: 'cell-nowrap', render: (row) => <span className="strong">{row.name}</span> },
    { key: 'employee_no', title: '工号', className: 'mono cell-nowrap', render: (row) => row.employee_no || '-' },
    { key: 'department', title: '部门', render: (row) => row.department || '-' },
    { key: 'title', title: '职务', render: (row) => row.title || '-' },
    { key: 'phone', title: '联系电话', className: 'cell-nowrap', render: (row) => row.phone || '-' },
    {
      key: 'zones',
      title: '任职片区',
      render: (row) => {
        const zones = row.zones || []
        if (!zones.length) return <span className="muted">未任职</span>
        return (
          <div className="stack" style={{ gap: 2 }}>
            {zones.map((assignment) => (
              <Tag key={assignment.zone_id} tone={ROLE_TONE[assignment.role] || 'neutral'}>
                {assignment.zone?.name} · {assignment.role_label}
              </Tag>
            ))}
          </div>
        )
      }
    },
    {
      key: 'status',
      title: '状态',
      render: (row) => <Tag tone={PERSON_STATUS_TONE[row.status]}>{row.status_label}</Tag>
    },
    {
      key: 'actions',
      title: '操作',
      align: 'right',
      render: (row) => (
        <div className="btn-group">
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => navigate(`/exceedances?manager_id=${row.id}`)}
          >
            名下超标
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
      emptyText="暂无责任人, 可先新增责任人再分配到片区"
      emptyIcon="👤"
    />
  )
}
