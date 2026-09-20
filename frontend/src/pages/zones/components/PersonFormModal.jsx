import { useEffect, useState } from 'react'
import Modal from '../../../components/common/Modal.jsx'
import { Field, Input, Select, Textarea } from '../../../components/common/FormField.jsx'
import { Alert } from '../../../components/common/Feedback.jsx'

const EMPTY = {
  name: '',
  employee_no: '',
  phone: '',
  department: '',
  title: '',
  status: 'active',
  remark: ''
}

const STATUS_OPTIONS = [
  { value: 'active', label: '在岗' },
  { value: 'inactive', label: '离岗' }
]

function toForm(person) {
  if (!person) return { ...EMPTY }
  return {
    name: person.name ?? '',
    employee_no: person.employee_no ?? '',
    phone: person.phone ?? '',
    department: person.department ?? '',
    title: person.title ?? '',
    status: person.status ?? 'active',
    remark: person.remark ?? ''
  }
}

export default function PersonFormModal({ open, person, onClose, onSubmit }) {
  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [message, setMessage] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!open) return
    setForm(toForm(person))
    setErrors({})
    setMessage(null)
  }, [open, person])

  const set = (key) => (event) => {
    setForm({ ...form, [key]: event.target.value })
    setErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setMessage(null)
    try {
      const payload = { ...form }
      Object.keys(payload).forEach((key) => {
        if (payload[key] === '') payload[key] = null
      })
      await onSubmit(payload)
    } catch (error) {
      setErrors(error.fields || {})
      setMessage(error.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      wide
      title={person ? `编辑责任人 · ${person.name}` : '新增责任人'}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={busy}>
            取消
          </button>
          <button type="submit" form="person-form" className="btn btn-primary" disabled={busy}>
            {busy ? '保存中...' : '保存'}
          </button>
        </>
      }
    >
      <form id="person-form" className="stack" onSubmit={submit}>
        {message ? <Alert tone="error">{message}</Alert> : null}
        <div className="form-grid">
          <Field label="姓名" required error={errors.name}>
            <Input value={form.name} onChange={set('name')} invalid={Boolean(errors.name)} placeholder="责任人姓名" />
          </Field>
          <Field label="工号" error={errors.employee_no} hint="全局唯一, 可不填">
            <Input value={form.employee_no || ''} onChange={set('employee_no')} invalid={Boolean(errors.employee_no)} />
          </Field>
          <Field label="联系电话" error={errors.phone}>
            <Input value={form.phone || ''} onChange={set('phone')} placeholder="手机号 / 座机" />
          </Field>
          <Field label="所属部门" error={errors.department}>
            <Input value={form.department || ''} onChange={set('department')} />
          </Field>
          <Field label="职务" error={errors.title}>
            <Input value={form.title || ''} onChange={set('title')} placeholder="如: 片区负责人" />
          </Field>
          <Field label="在岗状态" required error={errors.status}>
            <Select value={form.status} onChange={set('status')} options={STATUS_OPTIONS} />
          </Field>
          <Field label="备注" error={errors.remark} className="span-2">
            <Textarea value={form.remark || ''} onChange={set('remark')} placeholder="专业方向、值班安排等" />
          </Field>
        </div>
      </form>
    </Modal>
  )
}
