import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  clearJobQueue,
  deleteJob,
  fetchMetadataErrors,
  pauseJobs,
  refreshMetadata,
  refreshProviders,
  resolveMetadataError,
  resumeJobs,
  retryAllMetadataErrors,
  retryMetadata,
} from '../api'
import { isJobActive, useJobStatus } from '../hooks/useJobStatus'

const ERROR_LABELS = {
  search_miss: 'No TMDB match',
  tmdb_error: 'TMDB fetch failed',
  network: 'Network error',
  unknown: 'Unknown error',
  config: 'Not configured',
}

const JOB_LABELS = {
  metadata_import: 'Importing metadata',
  provider_refresh: 'Refreshing providers',
  metadata_rescan: 'Rescanning metadata',
  single_metadata: 'Refreshing metadata',
  image_download: 'Caching images',
}

function jobLabel(job) {
  return job?.label || JOB_LABELS[job?.job_type] || 'Background job'
}

function JobProgress({ job }) {
  if (!job) return null
  return (
    <div className="job-progress">
      <div className="job-progress__header">
        <strong>{jobLabel(job)}</strong>
        {job.running ? (
          <span className="job-progress__badge job-progress__badge--running">Running</span>
        ) : job.cancelled ? (
          <span className="job-progress__badge job-progress__badge--cancelled">Cancelled</span>
        ) : (
          <span className="job-progress__badge job-progress__badge--queued">Queued</span>
        )}
      </div>
      <p className="overview">
        {job.completed} / {job.total} complete
        {job.failed > 0 && ` (${job.failed} failed)`}
      </p>
      {job.current_item && (
        <p className="overview job-progress__current">Current: {job.current_item}</p>
      )}
      {job.total > 0 && (
        <div className="job-progress__bar" aria-hidden="true">
          <div
            className="job-progress__fill"
            style={{ width: `${Math.round(((job.completed + job.failed) / job.total) * 100)}%` }}
          />
        </div>
      )}
    </div>
  )
}

export default function JobsPage() {
  const { status, refreshStatus } = useJobStatus()
  const [error, setError] = useState(null)
  const [actionLoading, setActionLoading] = useState(null)
  const [metadataErrors, setMetadataErrors] = useState([])
  const [errorsLoading, setErrorsLoading] = useState(true)

  const loadErrors = useCallback(() => {
    setErrorsLoading(true)
    return fetchMetadataErrors()
      .then(setMetadataErrors)
      .catch(console.error)
      .finally(() => setErrorsLoading(false))
  }, [])

  useEffect(() => {
    loadErrors()
    refreshStatus()
  }, [loadErrors, refreshStatus])

  const queue = status?.queue
  const queuedJobs = queue?.queued || []
  const currentJob = queue?.current
  const queueLength = queue?.queue_length ?? queuedJobs.length
  const isPaused = status?.paused || queue?.paused
  const hasWork = isJobActive(status) || queueLength > 0 || currentJob

  async function runAction(key, fn) {
    setError(null)
    setActionLoading(key)
    try {
      await fn()
      await refreshStatus()
      loadErrors()
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="jobs-page">
      <h1 className="page-title">Jobs &amp; Logs</h1>

      {error && <p className="settings-error">{error}</p>}

      <div className="jobs-summary">
        <div className="jobs-stat">
          <span className="jobs-stat__value">{queueLength}</span>
          <span className="jobs-stat__label">Queued</span>
        </div>
        <div className="jobs-stat">
          <span className="jobs-stat__value">{currentJob?.running ? 1 : 0}</span>
          <span className="jobs-stat__label">Running</span>
        </div>
        <div className="jobs-stat">
          <span className="jobs-stat__value">{metadataErrors.length}</span>
          <span className="jobs-stat__label">Errors</span>
        </div>
        <div className="jobs-stat">
          <span className={`jobs-stat__value${isPaused ? ' jobs-stat__value--paused' : ''}`}>
            {isPaused ? 'Paused' : 'Active'}
          </span>
          <span className="jobs-stat__label">Worker</span>
        </div>
      </div>

      <div className="section">
        <h2>Queue controls</h2>
        <p className="overview" style={{ marginBottom: '1rem' }}>
          Pause to stop processing after the current item finishes. Resume to continue. Delete individual
          queued jobs or clear the entire queue.
        </p>
        <div className="job-actions">
          {isPaused ? (
            <button
              type="button"
              className="job-actions__btn"
              disabled={actionLoading === 'resume'}
              onClick={() => runAction('resume', resumeJobs)}
            >
              {actionLoading === 'resume' ? 'Starting…' : 'Start worker'}
            </button>
          ) : (
            <button
              type="button"
              className="job-actions__btn"
              disabled={actionLoading === 'pause' || !hasWork}
              onClick={() => runAction('pause', pauseJobs)}
            >
              {actionLoading === 'pause' ? 'Pausing…' : 'Pause worker'}
            </button>
          )}
          <button
            type="button"
            className="job-actions__btn"
            disabled={actionLoading === 'clear' || queueLength === 0}
            onClick={() => runAction('clear', clearJobQueue)}
          >
            {actionLoading === 'clear' ? 'Clearing…' : 'Clear queue'}
          </button>
          <button
            type="button"
            className="job-actions__btn"
            disabled={actionLoading === 'providers'}
            onClick={() => runAction('providers', refreshProviders)}
          >
            {actionLoading === 'providers' ? 'Queueing…' : 'Queue provider refresh'}
          </button>
          <button
            type="button"
            className="job-actions__btn"
            disabled={actionLoading === 'metadata'}
            onClick={() => runAction('metadata', refreshMetadata)}
          >
            {actionLoading === 'metadata' ? 'Queueing…' : 'Queue metadata rescan'}
          </button>
        </div>
      </div>

      {currentJob && (
        <div className="section">
          <h2>Current job</h2>
          <div className="settings-panel">
            <JobProgress job={currentJob} />
            <button
              type="button"
              className="job-queue-item__delete"
              style={{ marginTop: '0.75rem' }}
              disabled={actionLoading === `cancel-${currentJob.id}`}
              onClick={() => runAction(`cancel-${currentJob.id}`, () => deleteJob(currentJob.id))}
            >
              {actionLoading === `cancel-${currentJob.id}` ? 'Stopping…' : 'Stop job'}
            </button>
          </div>
        </div>
      )}

      {queuedJobs.length > 0 && (
        <div className="section">
          <h2>Queued jobs ({queuedJobs.length})</h2>
          <ul className="job-queue-list">
            {queuedJobs.map((job) => (
              <li key={job.id} className="job-queue-item">
                <div className="job-queue-item__info">
                  <strong>{jobLabel(job)}</strong>
                  <span className="job-queue-item__meta">{job.total} items</span>
                </div>
                <button
                  type="button"
                  className="job-queue-item__delete"
                  disabled={actionLoading === `delete-${job.id}`}
                  onClick={() => runAction(`delete-${job.id}`, () => deleteJob(job.id))}
                >
                  {actionLoading === `delete-${job.id}` ? 'Deleting…' : 'Delete'}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!hasWork && (
        <p className="overview" style={{ marginBottom: '1.5rem' }}>
          No jobs in the queue.
          {status?.last_provider_refresh && (
            <>
              {' '}
              Last provider refresh: {new Date(status.last_provider_refresh).toLocaleString()}
            </>
          )}
          {status?.last_metadata_rescan && (
            <> · Last metadata rescan: {new Date(status.last_metadata_rescan).toLocaleString()}</>
          )}
        </p>
      )}

      {status?.schedule?.enabled && (
        <p className="overview" style={{ marginBottom: '1.5rem', fontSize: '0.85rem' }}>
          Daily schedule: providers at {String(status.schedule.provider_refresh_hour).padStart(2, '0')}:00,
          metadata rescan at {String(status.schedule.metadata_rescan_hour).padStart(2, '0')}:00
        </p>
      )}

      <div className="section">
        <h2>Metadata errors ({metadataErrors.length})</h2>
        {errorsLoading ? (
          <p className="overview">Loading errors…</p>
        ) : metadataErrors.length === 0 ? (
          <p className="overview">No metadata errors.</p>
        ) : (
          <>
            <p className="overview" style={{ marginBottom: '1rem' }}>
              Titles that failed to match or fetch from TMDB.
            </p>
            <div className="job-actions" style={{ marginBottom: '1rem' }}>
              <button
                type="button"
                className="job-actions__btn"
                disabled={actionLoading === 'retry-all'}
                onClick={() => runAction('retry-all', retryAllMetadataErrors)}
              >
                {actionLoading === 'retry-all' ? 'Queueing…' : `Retry all (${metadataErrors.length})`}
              </button>
            </div>
            <ul className="error-list">
              {metadataErrors.map((err) => (
                <li key={err.media_id} className="error-list__item">
                  <div className="error-list__header">
                    <Link to={`/media/${err.media_id}`} className="error-list__title">
                      {err.title}
                      {err.year ? ` (${err.year})` : ''}
                    </Link>
                    <span className={`badge badge--${err.media_type}`}>{err.media_type}</span>
                  </div>
                  <p className="error-list__message">
                    <strong>{ERROR_LABELS[err.error_type] || err.error_type}:</strong> {err.message}
                  </p>
                  <p className="error-list__date">{new Date(err.created_at).toLocaleString()}</p>
                  <div className="error-list__actions">
                    <button
                      type="button"
                      onClick={() =>
                        runAction(`retry-${err.media_id}`, () => retryMetadata(err.media_id))
                      }
                    >
                      Retry
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        runAction(`dismiss-${err.media_id}`, () =>
                          resolveMetadataError(err.media_id, { notes: 'Dismissed from jobs page' }),
                        )
                      }
                    >
                      Dismiss
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  )
}
