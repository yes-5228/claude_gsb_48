import { useEffect, useState } from 'react'
import Modal from '../../../components/common/Modal.jsx'
import { Field, Input, Select, Textarea } from '../../../components/common/FormField.jsx'
import { Alert } from '../../../components/common/Feedback.jsx'

const EMPTY = {
  name: '',
  employee_no: '',
  phone: '',
  department: '',
  role: 'officer',
  status: 'active',
  remark: ''
}

const ROLE_OPTIONS = [
  { value: 'leader', label: '片区负责人' },
  { value: 'officer', label: '运维专员' },
  { value: 'inspector', label: '督查员' }
]

const STATUS_OPTIONS = [
  { value: 'active', label: '在职' },
  { value: 'inactive', label: '离岗' }
]

function toForm(person) {
  if (!person) return { ...EMPTY }
  return {
    name: person.name ?? '',
    employee_no: person.employee_no ?? '',
    phone: person.phone ?? '',
    department: person.department ?? '',
    role: person.role ?? 'officer',
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
    if (open) {
      setForm(toForm(person))
      setErrors({})
      setMessage(null)
    }
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
      await onSubmit({
        ...form,
        employee_no: form.employee_no.trim() || null
      })
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
          <Field label="工号" error={errors.employee_no} hint="全局唯一, 可留空">
            <Input value={form.employee_no} onChange={set('employee_no')} placeholder="如: EMP-101" />
          </Field>
          <Field label="联系电话" error={errors.phone}>
            <Input value={form.phone} onChange={set('phone')} />
          </Field>
          <Field label="所属部门" error={errors.department}>
            <Input value={form.department} onChange={set('department')} placeholder="如: 环境监测中心" />
          </Field>
          <Field label="默认岗位" required error={errors.role}>
            <Select value={form.role} onChange={set('role')} options={ROLE_OPTIONS} />
          </Field>
          <Field label="状态" required error={errors.status}>
            <Select value={form.status} onChange={set('status')} options={STATUS_OPTIONS} />
          </Field>
          <Field label="备注" error={errors.remark} className="span-2">
            <Textarea value={form.remark} onChange={set('remark')} />
          </Field>
        </div>
        <div className="hint">保存后可在“片区详情 → 责任人”中把责任人安排到具体片区, 片区任职支持时间分段留痕。</div>
      </form>
    </Modal>
  )
}
