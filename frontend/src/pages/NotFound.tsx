import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Button, EmptyState } from '../components/ui'

export function NotFound() {
  const navigate = useNavigate()
  return (
    <div className="page">
      <PageHeader title="Not found" />
      <div className="card">
        <EmptyState
          title="This page doesn’t exist"
          message="The link may be broken or the page may have moved."
          action={<Button variant="primary" onClick={() => navigate('/')}>Back to dashboard</Button>}
        />
      </div>
    </div>
  )
}
