import { useEffect, useState } from 'react'
import Modal from '../../../components/common/Modal.jsx'
import { Field, Input } from '../../../components/common/FormField.jsx'
import { Alert } from '../../../components/common/Feedback.jsx'

export default function LeaveMembershipModal({ open, payload, onClose, onSubmit }) {
  const [reason, setReason] = useState('')
  const [changedBy, setChangedBy] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (open) {
      setReason('')
      setChangedBy('')
      setError(null)
    }
  }, [open])

  const submit = async (event) => {
    event.preventDefault()
    if (!reason.trim()) {
      setError('卸任必须填写变更原因, 以便历史追溯')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await onSubmit({
        membership_id: payload?.membership_id,
        change_reason: reason.trim(),
        changed_by: changedBy.trim() || null
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      title="办理责任人卸任"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={busy}>
            取消
          </button>
          <button type="submit" form="leave-form" className="btn btn-primary" disabled={busy}>
            {busy ? '提交中...' : '确认卸任'}
          </button>
        </>
      }
    >
      <form id="leave-form" className="stack" onSubmit={submit}>
        {error ? <Alert tone="error">{error}</Alert> : null}
        <div className="alert alert-warning">
          确认为「{payload?.name || ''}」办理卸任吗? 卸任后该责任人不再出现在当前名单, 但历史任职记录完整保留。
        </div>
        <Field label="变更原因" required>
          <Input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="如: 轮岗 / 离职 / 分工调整" />
        </Field>
        <Field label="操作人">
          <Input value={changedBy} onChange={(event) => setChangedBy(event.target.value)} />
        </Field>
      </form>
    </Modal>
  )
}
