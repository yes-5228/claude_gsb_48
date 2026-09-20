import { useEffect, useState } from 'react'
import Modal from '../../../components/common/Modal.jsx'
import { Field, Input, Select } from '../../../components/common/FormField.jsx'
import { Alert } from '../../../components/common/Feedback.jsx'
import { usePersonOptions } from '../../../hooks/useOptions.js'

const ROLE_OPTIONS = [
  { value: 'manager', label: '片区负责人' },
  { value: 'supervisor', label: '分管领导' },
  { value: 'engineer', label: '运维专员' }
]

const EMPTY = { person_id: '', role: 'manager', operator: '', note: '' }

/**
 * 分配责任人到片区, 或调整既有责任人角色。
 * mode = 'add' 时展示责任人下拉; mode = 'role' 时仅调整角色。
 */
export default function ManagerAssignModal({ open, mode, zone, manager, onClose, onSubmit }) {
  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [message, setMessage] = useState(null)
  const [busy, setBusy] = useState(false)
  const { data: personData } = usePersonOptions()

  useEffect(() => {
    if (!open) return
    setErrors({})
    setMessage(null)
    if (mode === 'role' && manager) {
      setForm({
        person_id: String(manager.person_id ?? manager.id),
        role: manager.role || 'manager',
        operator: '',
        note: ''
      })
    } else {
      setForm(EMPTY)
    }
  }, [open, mode, manager])

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
        person_id: Number(form.person_id),
        role: form.role,
        operator: form.operator || null,
        note: form.note || null
      })
    } catch (error) {
      setErrors(error.fields || {})
      setMessage(error.message)
    } finally {
      setBusy(false)
    }
  }

  const usedPersonIds = new Set((zone?.managers ?? []).map((item) => item.person_id))
  const personOptions = (personData?.items ?? [])
    .filter((item) => mode === 'role' || !usedPersonIds.has(item.id))
    .map((item) => ({
      value: String(item.id),
      label: item.employee_no ? `${item.name} (${item.employee_no})` : item.name
    }))

  return (
    <Modal
      open={open}
      title={
        mode === 'role'
          ? `调整角色 · ${manager?.person?.name || ''}`
          : `为「${zone?.name || ''}」分配责任人`
      }
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={busy}>
            取消
          </button>
          <button type="submit" form="manager-form" className="btn btn-primary" disabled={busy}>
            {busy ? '提交中...' : '确认'}
          </button>
        </>
      }
    >
      <form id="manager-form" className="stack" onSubmit={submit}>
        {message ? <Alert tone="error">{message}</Alert> : null}
        <Field label="责任人" required error={errors.person_id}>
          {mode === 'add' ? (
            <Select
              value={form.person_id}
              onChange={set('person_id')}
              placeholder="请选择在岗责任人"
              options={personOptions}
            />
          ) : (
            <Input value={manager?.person?.name || ''} disabled />
          )}
        </Field>
        <Field label="责任角色" required error={errors.role}>
          <Select value={form.role} onChange={set('role')} options={ROLE_OPTIONS} />
        </Field>
        <Field label="操作人" error={errors.operator}>
          <Input value={form.operator} onChange={set('operator')} placeholder="记录是谁执行的变动, 便于追溯" />
        </Field>
        <Field label="变动说明" error={errors.note}>
          <Input value={form.note} onChange={set('note')} placeholder="如: 季度轮岗 / 临时接管" />
        </Field>
      </form>
    </Modal>
  )
}
