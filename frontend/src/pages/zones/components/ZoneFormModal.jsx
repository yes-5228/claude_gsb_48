import { useEffect, useState } from 'react'
import Modal from '../../../components/common/Modal.jsx'
import { Field, Input, Select, Textarea } from '../../../components/common/FormField.jsx'
import { Alert } from '../../../components/common/Feedback.jsx'

const EMPTY = {
  code: '',
  name: '',
  description: '',
  status: 'active'
}

const STATUS_OPTIONS = [
  { value: 'active', label: '启用' },
  { value: 'inactive', label: '停用' }
]

function toForm(zone) {
  if (!zone) return { ...EMPTY }
  return {
    code: zone.code ?? '',
    name: zone.name ?? '',
    description: zone.description ?? '',
    status: zone.status ?? 'active'
  }
}

export default function ZoneFormModal({ open, zone, onClose, onSubmit }) {
  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [message, setMessage] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!open) return
    setForm(toForm(zone))
    setErrors({})
    setMessage(null)
  }, [open, zone])

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
      title={zone ? `编辑片区 · ${zone.code}` : '新增片区'}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={busy}>
            取消
          </button>
          <button type="submit" form="zone-form" className="btn btn-primary" disabled={busy}>
            {busy ? '保存中...' : '保存'}
          </button>
        </>
      }
    >
      <form id="zone-form" className="stack" onSubmit={submit}>
        {message ? <Alert tone="error">{message}</Alert> : null}
        <div className="form-grid">
          <Field label="片区编码" required error={errors.code} hint="全局唯一, 如 ZN-CENTER">
            <Input value={form.code} onChange={set('code')} invalid={Boolean(errors.code)} placeholder="ZN-01" />
          </Field>
          <Field label="片区名称" required error={errors.name}>
            <Input value={form.name} onChange={set('name')} invalid={Boolean(errors.name)} placeholder="如: 中心城区片区" />
          </Field>
          <Field label="片区状态" required error={errors.status}>
            <Select value={form.status} onChange={set('status')} options={STATUS_OPTIONS} />
          </Field>
          <Field label="片区说明" error={errors.description} className="span-2">
            <Textarea
              value={form.description || ''}
              onChange={set('description')}
              placeholder="覆盖范围、职责描述等"
            />
          </Field>
        </div>
      </form>
    </Modal>
  )
}
