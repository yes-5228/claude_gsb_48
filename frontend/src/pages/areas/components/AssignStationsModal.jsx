import { useEffect, useState } from 'react'
import Modal from '../../../components/common/Modal.jsx'
import { Field, Input, Select } from '../../../components/common/FormField.jsx'
import { Alert } from '../../../components/common/Feedback.jsx'
import { toDateTimeInput } from '../../../utils/format.js'

export default function AssignStationsModal({ open, area, stations, onClose, onSubmit }) {
  const [selected, setSelected] = useState([])
  const [effectiveFrom, setEffectiveFrom] = useState(toDateTimeInput())
  const [reason, setReason] = useState('')
  const [changedBy, setChangedBy] = useState('')
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (open) {
      setSelected([])
      setEffectiveFrom(toDateTimeInput())
      setReason('')
      setChangedBy('')
      setErrors({})
    }
  }, [open])

  const toggle = (id) =>
    setSelected((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]))

  const submit = async (event) => {
    event.preventDefault()
    if (selected.length === 0) {
      setErrors({ station_ids: '请至少勾选一个监测点' })
      return
    }
    if (!reason.trim()) {
      setErrors({ change_reason: '划转必须填写变更原因, 以便历史追溯' })
      return
    }
    setBusy(true)
    try {
      await onSubmit({
        area_id: area.id,
        station_ids: selected,
        effective_from: effectiveFrom.replace('T', ' '),
        change_reason: reason.trim(),
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
      wide
      title={`划转监测点至「${area?.name || ''}」`}
      onClose={onClose}
      footer={
        <>
          <span className="hint" style={{ marginRight: 'auto' }}>
            已选 {selected.length} 个点位 · 划转将记录生效时间并保留原片区归属历史
          </span>
          <button type="button" className="btn" onClick={onClose} disabled={busy}>
            取消
          </button>
          <button type="submit" form="assign-form" className="btn btn-primary" disabled={busy}>
            {busy ? '提交中...' : '确认划转'}
          </button>
        </>
      }
    >
      <form id="assign-form" className="stack" onSubmit={submit}>
        {errors.station_ids ? <Alert tone="error">{errors.station_ids}</Alert> : null}
        {errors.effective_from ? <Alert tone="error">{errors.effective_from}</Alert> : null}
        {errors.change_reason ? <Alert tone="error">{errors.change_reason}</Alert> : null}
        <div className="table-wrap" style={{ maxHeight: 320, overflowY: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 44 }} />
                <th>监测点编码</th>
                <th>监测点名称</th>
                <th>当前所属片区</th>
              </tr>
            </thead>
            <tbody>
              {stations.map((station) => (
                <tr key={station.id} className="clickable" onClick={() => toggle(station.id)}>
                  <td onClick={(event) => event.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selected.includes(station.id)}
                      onChange={() => toggle(station.id)}
                    />
                  </td>
                  <td className="mono">{station.code}</td>
                  <td>{station.name}</td>
                  <td className="muted">{station.area}</td>
                </tr>
              ))}
              {stations.length === 0 ? (
                <tr>
                  <td colSpan={4} className="muted" style={{ textAlign: 'center', padding: 16 }}>
                    没有可划转的监测点
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        <div className="form-grid">
          <Field label="生效时间" required error={errors.effective_from} hint="该时刻起监测点归属新片区, 历史数据仍按旧片区汇总">
            <Input type="datetime-local" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} />
          </Field>
          <Field label="操作人" error={errors.changed_by}>
            <Input value={changedBy} onChange={(e) => setChangedBy(e.target.value)} placeholder="执行划转的工作人员" />
          </Field>
          <Field label="变更原因" required error={errors.change_reason} className="span-2">
            <Input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="如: 行政区划调整 / 管理职能移交 / 站点搬迁"
            />
          </Field>
        </div>
      </form>
    </Modal>
  )
}
