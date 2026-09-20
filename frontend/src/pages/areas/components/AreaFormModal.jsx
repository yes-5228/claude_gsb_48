import { useEffect, useState } from 'react'
import Modal from '../../../components/common/Modal.jsx'
import { Field, Input, Select, Textarea } from '../../../components/common/FormField.jsx'
import { Alert } from '../../../components/common/Feedback.jsx'

const EMPTY = {
  code: '',
  name: '',
  manager: '',
  phone: '',
  status: 'active',
  remark: ''
}

const STATUS_OPTIONS = [
  { value: 'active', label: '启用' },
  { value: 'inactive', label: '停用' }
]

function toForm(area) {
  if (!area) return { ...EMPTY }
  return {
    code: area.code ?? '',
    name: area.name ?? '',
    manager: area.manager ?? '',
    phone: area.phone ?? '',
    status: area.status ?? 'active',
    remark: area.remark ?? ''
  }
}

export default function AreaFormModal({ open, area, onClose, onSubmit }) {
  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [message, setMessage] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!open) return
    setForm(toForm(area))
    setErrors({})
    setMessage(null)
  }, [open, area])

  const set = (key) => (event) => {
    setForm({ ...form, [key]: event.target.value })
    setErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setMessage(null)
    try {
      await onSubmit(form)
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
      title={area ? `编辑片区 · ${area.code}` : '新增片区'}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={busy}>
            取消
          </button>
          <button type="submit" form="area-form" className="btn btn-primary" disabled={busy}>
            {busy ? '保存中...' : '保存'}
          </button>
        </>
      }
    >
      <form id="area-form" className="stack" onSubmit={submit}>
        {message ? <Alert tone="error">{message}</Alert> : null}
        <div className="form-grid">
          <Field label="片区编码" required error={errors.code} hint="全局唯一, 如 GRID-CITY">
            <Input value={form.code} onChange={set('code')} invalid={Boolean(errors.code)} placeholder="如: GRID-CITY" />
          </Field>
          <Field label="片区名称" required error={errors.name}>
            <Input value={form.name} onChange={set('name')} invalid={Boolean(errors.name)} placeholder="如: 中心城区片区" />
          </Field>
          <Field label="片区主管" error={errors.manager}>
            <Input value={form.manager} onChange={set('manager')} placeholder="主管姓名" />
          </Field>
          <Field label="联系电话" error={errors.phone}>
            <Input value={form.phone} onChange={set('phone')} placeholder="办公电话 / 手机" />
          </Field>
          <Field label="状态" required error={errors.status}>
            <Select value={form.status} onChange={set('status')} options={STATUS_OPTIONS} />
          </Field>
          <Field label="备注" error={errors.remark} className="span-2">
            <Textarea value={form.remark} onChange={set('remark')} placeholder="片区职责范围、说明等" />
          </Field>
        </div>
      </form>
    </Modal>
  )
}
