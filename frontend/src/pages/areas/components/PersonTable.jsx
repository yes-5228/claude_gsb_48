import DataTable from '../../../components/common/DataTable.jsx'
import Tag from '../../../components/common/Tag.jsx'

export default function PersonTable({ rows, loading, onEdit, onDelete }) {
  const columns = [
    { key: 'name', title: '姓名', render: (row) => <span className="strong">{row.name}</span> },
    { key: 'employee_no', title: '工号', className: 'mono', render: (row) => row.employee_no || '-' },
    { key: 'role_label', title: '默认岗位' },
    { key: 'department', title: '部门', render: (row) => row.department || '-' },
    { key: 'phone', title: '电话', render: (row) => row.phone || '-' },
    {
      key: 'areas',
      title: '当前任职片区',
      render: (row) =>
        row.areas?.length ? (
          <div className="inline" style={{ gap: 4, flexWrap: 'wrap' }}>
            {row.areas.map((area) => (
              <Tag key={area.id} tone="primary">
                {area.name}
              </Tag>
            ))}
          </div>
        ) : (
          <span className="muted">未安排</span>
        )
    },
    {
      key: 'status',
      title: '状态',
      render: (row) => <Tag tone={row.status === 'active' ? 'success' : 'neutral'}>{row.status_label}</Tag>
    },
    {
      key: 'actions',
      title: '操作',
      align: 'right',
      render: (row) => (
        <div className="btn-group">
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
    <DataTable columns={columns} rows={rows} loading={loading} emptyText="还没有责任人, 点击右上角“新增责任人”" emptyIcon="👤" />
  )
}
