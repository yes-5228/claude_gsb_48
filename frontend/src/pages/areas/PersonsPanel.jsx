import { useCallback, useState } from 'react'
import { createPerson, deletePerson, listPersons, updatePerson } from '../../api/areas.js'
import Pagination from '../../components/common/Pagination.jsx'
import { SectionCard } from '../../components/common/Card.jsx'
import ConfirmDialog from '../../components/common/ConfirmDialog.jsx'
import { Alert } from '../../components/common/Feedback.jsx'
import { useToast } from '../../components/common/ToastProvider.jsx'
import { useListQuery } from '../../hooks/useListQuery.js'
import { resetOptionCache } from '../../hooks/useOptions.js'
import PersonFormModal from './components/PersonFormModal.jsx'
import PersonTable from './components/PersonTable.jsx'

export default function PersonsPanel() {
  const toast = useToast()
  const query = useListQuery(listPersons, {})
  const [formState, setFormState] = useState({ open: false, person: null })
  const [pendingDelete, setPendingDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const handleSubmit = useCallback(
    async (payload) => {
      if (formState.person) {
        await updatePerson(formState.person.id, payload)
        toast.success(`责任人 ${payload.name} 已更新`)
      } else {
        await createPerson(payload)
        toast.success(`责任人 ${payload.name} 已创建`)
      }
      setFormState({ open: false, person: null })
      resetOptionCache()
      query.reload()
    },
    [formState.person, query, toast]
  )

  const handleDelete = useCallback(async () => {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await deletePerson(pendingDelete.id)
      toast.success(`责任人 ${pendingDelete.name} 已删除`)
      setPendingDelete(null)
      resetOptionCache()
      query.reload()
    } catch (error) {
      toast.error(error.message)
      setPendingDelete(null)
    } finally {
      setDeleting(false)
    }
  }, [pendingDelete, query, toast])

  return (
    <>
      {query.error ? <Alert tone="error">{query.error.message}</Alert> : null}
      <SectionCard
        title="责任人台账"
        hint="责任人通过“片区详情 → 责任人”安排到片区, 任职与卸任均保留历史"
        actions={
          <button type="button" className="btn btn-primary" onClick={() => setFormState({ open: true, person: null })}>
            + 新增责任人
          </button>
        }
      >
        <PersonTable
          rows={query.items}
          loading={query.loading}
          onEdit={(row) => setFormState({ open: true, person: row })}
          onDelete={(row) => setPendingDelete(row)}
        />
        <Pagination
          page={query.page}
          pages={query.pages}
          total={query.total}
          pageSize={query.pageSize}
          onPageChange={query.setPage}
          onPageSizeChange={query.setPageSize}
        />
      </SectionCard>

      <PersonFormModal
        open={formState.open}
        person={formState.person}
        onClose={() => setFormState({ open: false, person: null })}
        onSubmit={handleSubmit}
      />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        danger
        busy={deleting}
        title="删除责任人"
        message={`确认删除责任人「${pendingDelete?.name || ''}」吗?`}
        detail="已有任职记录的责任人不能删除, 请改用“离岗”状态以保留历史。"
        confirmText="确认删除"
        onConfirm={handleDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </>
  )
}
