import { useEffect, useState } from 'react'
import Modal from '../../../components/common/Modal.jsx'
import { Field, Input, Select } from '../../../components/common/FormField.jsx'
import { Alert } from '../../../components/common/Feedback.jsx'
import { toDateTimeInput } from '../../../utils/format.js'

export default function MembershipModal({ open, area, persons, onClose, onSubmit }) {
  const [personId, setPersonId] = useState('')
  const [role, setRole] = useState('officer')
  const [effectiveFrom, setEffectiveFrom] = useState(toDateTimeInput())
  const [reason, setReason] = useState('')
  const [changedBy, setChangedBy] = useState('')
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (open) {
      setPersonId('')
      setRole('officer')
      setEffectiveFrom(toDateTimeInput())
      setReason('')
      setChangedBy('')
      setErrors({})
    }
  }, [open])

  const submit = async (event) => {
    event.preventDefault()
    if (!personId) {
      setErrors({ person_id: '请选择责任人' })
      return
    }
    setBusy(true)
    try {
      await onSubmit({
        area_id: area.id,
        person_id: Number(personId),
        role,
        effective_from: effectiveFrom.replace('T', ' '),
        change_reason: reason.trim() || null,
        changed_by: changedBy.trim() || null
      })
    } catch (error) {
      setErrors(error.fields || {})
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      title={`为「${area?.name || ''}」添加责任人`}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={busy}>
            取消
          </button>
          <button type="submit" form="membership-form" className="btn btn-primary" disabled={busy}>
            {busy ? '提交中...' : '确认添加'}
          </button>
        </>
      }
    >
      <form id="membership-form" className="stack" onSubmit={submit}>
        {Object.keys(errors).length ? <Alert tone="error">{Object.values(errors)[0]}</Alert> : null}
        <div className="form-grid">
          <Field label="责任人" required error={errors.person_id} className="span-2">
            <Select
              value={personId}
              onChange={(event) => setPersonId(event.target.value)}
              placeholder="选择责任人"
              options={persons.map((person) => ({
                value: String(person.id),
                label: `${person.name}${person.employee_no ? ` (${person.employee_no})` : ''} · ${person.role_label}`
              }))}
            />
          </Field>
          <Field label="在片区内岗位" required>
            <Select
              value={role}
              onChange={(event) => setRole(event.target.value)}
              options={[
                { value: 'leader', label: '片区负责人' },
                { value: 'officer', label: '运维专员' },
                { value: 'inspector', label: '督查员' }
              ]}
            />
          </Field>
          <Field label="任职生效时间" required>
            <Input type="datetime-local" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} />
          </Field>
          <Field label="变更原因" className="span-2">
            <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="如: 新增分工 / 岗位调整" />
          </Field>
          <Field label="操作人">
            <Input value={changedBy} onChange={(e) => setChangedBy(e.target.value)} />
          </Field>
        </div>
      </form>
    </Modal>
  )
}
