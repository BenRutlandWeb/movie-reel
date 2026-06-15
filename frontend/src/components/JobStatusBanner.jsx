import { Link } from 'react-router-dom'
import { isJobActive, useJobStatus } from '../hooks/useJobStatus'

const JOB_LABELS = {
  metadata_import: 'Importing metadata',
  provider_refresh: 'Refreshing providers',
  metadata_rescan: 'Rescanning metadata',
  single_metadata: 'Refreshing metadata',
}

export default function JobStatusBanner() {
  const { status } = useJobStatus()

  if (!isJobActive(status)) return null

  const label = status.label || JOB_LABELS[status.job_type] || 'Background job'
  const progress =
    status.running && status.total > 0
      ? `${status.completed} / ${status.total}`
      : 'Queued'

  return (
    <div className="job-status-banner" role="status" aria-live="polite">
      <span className="job-status-banner__text">
        <strong>{label}</strong>
        <span>{progress}</span>
        {status.current_item && (
          <span className="job-status-banner__current">{status.current_item}</span>
        )}
      </span>
      <Link to="/settings" className="job-status-banner__link">
        View details
      </Link>
    </div>
  )
}
