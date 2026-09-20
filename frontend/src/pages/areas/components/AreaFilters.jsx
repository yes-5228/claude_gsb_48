import { useEffect, useState } from 'react'
import { FilterPanel } from '../../../components/common/Card.jsx'
import { Field, Input, Select } from '../../../components/common/FormField.jsx'

const STATUS_OPTIONS = [
  { value: 'active', label: '启用' },
  { value: 'inactive', label: '停用' }
]

export default function AreaFilters({ value, loading, onSubmit, onReset }) {
  const [draft, setDraft] = useState(value)

  useEffect(() => {
    setDraft(value)
  }, [value])

  const update = (key) => (event) => setDraft({ ...draft, [key]: event.target.value })

  return (
    <FilterPanel
      loading={loading}
      onSearch={() => onSubmit(draft)}
      onReset={() => {
        setDraft({ keyword: '', status: '' })
        onReset()
      }}
    >
      <Field label="关键字">
        <Input
          placeholder="片区名称 / 编码 / 主管"
          value={draft.keyword || ''}
          onChange={update('keyword')}
          onKeyDown={(event) => event.key === 'Enter' && onSubmit(draft)}
        />
      </Field>
      <Field label="状态">
        <Select value={draft.status || ''} onChange={update('status')} placeholder="全部状态" options={STATUS_OPTIONS} />
      </Field>
    </FilterPanel>
  )
}
