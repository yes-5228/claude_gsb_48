import { useEffect, useState } from 'react'
import Modal from '../../../components/common/Modal.jsx'
import { Checkbox, Field, Input, Select, Textarea } from '../../../components/common/FormField.jsx'
import { Alert } from '../../../components/common/Feedback.jsx'
import { useAreaOptions } from '../../../hooks/useOptions.js'

const EMPTY = {
  code: '',
  name: '',
  area_id: '',
  area: '',
  address: '',
  station_type: 'ambient',
  status: 'active',
  longitude: '',
  latitude: '',
  installed_at: '',
  change_reason: '',
  remark: ''
}

const TYPE_OPTIONS = [
  { value: 'ambient', label: '环境空气' },
  { value: 'traffic', label: '道路交通' },
  { value: 'background', label: '区域背景' },
  { value: 'industrial', label: '工业园区' },
  { value: 'rural', label: '农村站点' }
]

const STATUS_OPTIONS = [
  { value: 'active', label: '运行中' },
  { value: 'maintenance', label: '维护中' },
  { value: 'offline', label: '停用' }
]

function toForm(station) {
  if (!station) return { ...EMPTY }
  return {
    code: station.code ?? '',
    name: station.name ?? '',
    area_id: station.area_id ?? '',
    area: station.area ?? '',
    address: station.address ?? '',
    station_type: station.station_type ?? 'ambient',
    status: station.status ?? 'active',
    longitude: station.longitude ?? '',
    latitude: station.latitude ?? '',
    installed_at: station.installed_at ?? '',
    change_reason: '',
    remark: station.remark ?? ''
  }
}

export default function StationFormModal({ open, station, areas = [], onClose, onSubmit }) {
  const { data: areaData } = useAreaOptions()
  const areaOptions = areas.length ? areas.map((item) => ({ value: String(item.id), label: item.name }))
    : (areaData?.items ?? []).map((item) => ({ value: String(item.id), label: item.name }))
  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [message, setMessage] = useState(null)
  const [busy, setBusy] = useState(false)
  const [autoCode, setAutoCode] = useState(true)

  useEffect(() => {
    if (!open) return
    setForm(toForm(station))
    setErrors({})
    setMessage(null)
    setAutoCode(!station)
  }, [open, station])

  useEffect(() => {
    if (!open || !autoCode || station) return
    const stamp = new Date()
    const sequence = String(stamp.getMonth() + 1).padStart(2, '0') + String(stamp.getDate()).padStart(2, '0')
    setForm((prev) => (prev.code ? prev : { ...prev, code: `SZ-AQ-${sequence}` }))
  }, [open, autoCode, station])

  const set = (key) => (event) => {
    setForm({ ...form, [key]: event.target.value })
    setErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setMessage(null)
    try {
      // 编辑时修改了片区, 必须填写变更原因用于历史留痕
      const areaChanged =
        station && form.area_id !== '' && Number(form.area_id) !== Number(station.area_id || '')
      if (areaChanged && !form.change_reason.trim()) {
        setErrors({ change_reason: '调整归属片区必须填写变更原因' })
        setBusy(false)
        return
      }
      const payload = {
        ...form,
        area_id: form.area_id === '' ? undefined : Number(form.area_id),
        longitude: form.longitude === '' ? null : Number(form.longitude),
        latitude: form.latitude === '' ? null : Number(form.latitude),
        installed_at: form.installed_at || null,
        change_reason: areaChanged ? form.change_reason.trim() : undefined
      }
      if (!station && !form.area_id) {
        // 新建时允许直接填写新片区名 (后端自动建片区), 不传 area_id
        delete payload.area_id
      }
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
      title={station ? `编辑监测点 · ${station.code}` : '新增监测点'}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={busy}>
            取消
          </button>
          <button type="submit" form="station-form" className="btn btn-primary" disabled={busy}>
            {busy ? '保存中...' : '保存'}
          </button>
        </>
      }
    >
      <form id="station-form" className="stack" onSubmit={submit}>
        {message ? <Alert tone="error">{message}</Alert> : null}
        <div className="form-grid">
          <Field label="监测点编码" required error={errors.code} hint="全局唯一, 建议使用 城市-类型-序号">
            <Input value={form.code} onChange={set('code')} invalid={Boolean(errors.code)} placeholder="SZ-AQ-009" />
          </Field>
          <Field label="监测点名称" required error={errors.name}>
            <Input value={form.name} onChange={set('name')} invalid={Boolean(errors.name)} placeholder="如: 市民中心站" />
          </Field>
          <Field label="所属片区" required error={errors.area_id || errors.area} hint="从片区管理中选择, 或直接输入新片区名自动建档">
            <Select
              value={form.area_id === '' ? '' : String(form.area_id)}
              onChange={(event) => {
                const value = event.target.value
                setForm({
                  ...form,
                  area_id: value,
                  area: areaOptions.find((item) => item.value === value)?.label || form.area
                })
              }}
              invalid={Boolean(errors.area_id || errors.area)}
              placeholder="选择片区"
              options={areaOptions}
            />
          </Field>
          <Field label="或新片区名称" error={errors.area} hint="列表中没有时直接填写, 保存后自动建立片区">
            <Input
              value={form.area_id ? '' : form.area}
              onChange={(event) => setForm({ ...form, area_id: '', area: event.target.value })}
              disabled={Boolean(form.area_id)}
              placeholder="如: 临港新城片区"
            />
          </Field>
          <Field label="详细地址" error={errors.address}>
            <Input value={form.address} onChange={set('address')} placeholder="道路 + 门牌" />
          </Field>
          <Field label="监测点类型" required error={errors.station_type}>
            <Select value={form.station_type} onChange={set('station_type')} options={TYPE_OPTIONS} />
          </Field>
          <Field label="运行状态" required error={errors.status}>
            <Select value={form.status} onChange={set('status')} options={STATUS_OPTIONS} />
          </Field>
          <Field label="经度" error={errors.longitude} hint="-180 ~ 180">
            <Input type="number" step="0.0001" value={form.longitude} onChange={set('longitude')} invalid={Boolean(errors.longitude)} />
          </Field>
          <Field label="纬度" error={errors.latitude} hint="-90 ~ 90">
            <Input type="number" step="0.0001" value={form.latitude} onChange={set('latitude')} invalid={Boolean(errors.latitude)} />
          </Field>
          <Field label="投运日期" error={errors.installed_at}>
            <Input type="date" value={form.installed_at} onChange={set('installed_at')} />
          </Field>
          <Field label="备注" error={errors.remark} className="span-2">
            <Textarea value={form.remark} onChange={set('remark')} placeholder="点位周边环境、运维说明等" />
          </Field>
          {station ? (
            <Field
              label="归属变更原因"
              error={errors.change_reason}
              className="span-2"
              hint="仅当调整所属片区时需要填写, 将写入归属历史"
            >
              <Input
                value={form.change_reason}
                onChange={set('change_reason')}
                placeholder="如: 行政区划调整、点位移交其他片区"
              />
            </Field>
          ) : null}
        </div>
        {!station ? (
          <Checkbox
            label="自动生成建议编码"
            checked={autoCode}
            onChange={(event) => setAutoCode(event.target.checked)}
          />
        ) : null}
      </form>
    </Modal>
  )
}
