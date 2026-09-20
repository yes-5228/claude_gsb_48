import { useEffect, useState } from 'react'
import Modal from '../../../components/common/Modal.jsx'
import { Field, Input, Select } from '../../../components/common/FormField.jsx'
import { Alert } from '../../../components/common/Feedback.jsx'
import { useZoneOptions } from '../../../hooks/useOptions.js'

/**
 * 批量把监测点归属到某个片区(或解除归属), 每次变动都会在后端追加历史记录。
 */
export default function BatchZoneAssignModal({ open, stationIds, onClose, onSubmit }) {
  const [zoneId, setZoneId] = useState('')
  const [unassign, setUnassign] = useState(false)
  const [note, setNote] = useState('')
  const [operator, setOperator] = useState('')
  const [message, setMessage] = useState(null)
  const [busy, setBusy] = useState(false)
  const { data: zoneData } = useZoneOptions()

  useEffect(() => {
    if (!open) return
    setZoneId('')
    setUnassign(false)
    setNote('')
    setOperator('')
    setMessage(null)
  }, [open])

  const submit = async (event) => {
    event.preventDefault()
    if (!unassign && !zoneId) {
      setMessage('请选择目标片区, 或勾选“解除归属”')
      return
    }
    setBusy(true)
    setMessage(null)
    try {
      await onSubmit({
        station_ids: stationIds,
        zone_id: unassign ? null : Number(zoneId),
        note: note || null,
        operator: operator || null
      })
    } catch (error) {
      setMessage(error.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      title={`批量归属片区 (${stationIds.length} 个监测点)`}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={busy}>
            取消
          </button>
          <button type="submit" form="batch-zone-form" className="btn btn-primary" disabled={busy}>
            {busy ? '提交中...' : '确认归属'}
          </button>
        </>
      }
    >
      <form id="batch-zone-form" className="stack" onSubmit={submit}>
        {message ? <Alert tone="error">{message}</Alert> : null}
        <Alert tone="info">归属调整会逐点写入历史流水, 包含操作人与说明, 历史记录不可修改。</Alert>
        <Field label="目标片区" required={!unassign}>
          <Select
            value={unassign ? '' : zoneId}
            disabled={unassign}
            onChange={(event) => setZoneId(event.target.value)}
            placeholder="选择片区"
            options={(zoneData?.items ?? []).map((zone) => ({ value: String(zone.id), label: zone.name }))}
          />
        </Field>
        <Field label="解除归属">
          <label className="checkbox">
            <input
              type="checkbox"
              checked={unassign}
              onChange={(event) => setUnassign(event.target.checked)}
            />
            <span>将选中的点位移出片区(标记为未划分)</span>
          </label>
        </Field>
        <Field label="操作人">
          <Input value={operator} onChange={(event) => setOperator(event.target.value)} placeholder="记录是谁执行的调整" />
        </Field>
        <Field label="变动说明">
          <Input value={note} onChange={(event) => setNote(event.target.value)} placeholder="如: 季度片区重新划分" />
        </Field>
      </form>
    </Modal>
  )
}
