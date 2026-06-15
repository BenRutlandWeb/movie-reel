import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  deleteCollection,
  exportCollection,
  fetchAppSettings,
  fetchMetadataErrors,
  fetchProviders,
  importStubs,
  refreshMetadata,
  refreshProviders,
  resolveMetadataError,
  retryMetadata,
  searchTmdb,
  updateAppSettings,
} from '../api'
import ConfirmDialog from '../components/ConfirmDialog'
import { isJobActive, useJobStatus } from '../hooks/useJobStatus'
import { getSelectedStreamers, setSelectedStreamers } from '../utils/streamerPrefs'

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

function normalizeImportItems(data) {
  if (!data?.items?.length) {
    throw new Error('No items found in import file')
  }
  return data.items.map((item) => ({
    title: item.title,
    year: item.year ?? null,
    media_type: item.media_type,
    seasons: item.seasons ?? [],
    tags: item.tags ?? [],
  }))
}

export default function SettingsPage({ onImport }) {
  const fileRef = useRef()
  const { status, setStatus, refreshStatus } = useJobStatus()
  const wasJobActive = useRef(false)
  const [importing, setImporting] = useState(false)
  const [error, setError] = useState(null)
  const [providers, setProviders] = useState([])
  const [selectedIds, setSelectedIds] = useState(() => getSelectedStreamers())
  const [providersLoading, setProvidersLoading] = useState(true)
  const [refreshingProviders, setRefreshingProviders] = useState(false)
  const [refreshingMetadata, setRefreshingMetadata] = useState(false)
  const [providerSearch, setProviderSearch] = useState('')
  const [metadataErrors, setMetadataErrors] = useState([])
  const [errorsLoading, setErrorsLoading] = useState(true)
  const [fixingId, setFixingId] = useState(null)
  const [fixResults, setFixResults] = useState({})
  const [appSettings, setAppSettings] = useState(null)
  const [tmdbKeyInput, setTmdbKeyInput] = useState('')
  const [tmdbRegionInput, setTmdbRegionInput] = useState('US')
  const [savingTmdb, setSavingTmdb] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [deletingCollection, setDeletingCollection] = useState(false)

  const loadAppSettings = useCallback(() => {
    return fetchAppSettings()
      .then((data) => {
        setAppSettings(data)
        setTmdbRegionInput(data.tmdb_region || 'US')
      })
      .catch(console.error)
  }, [])

  const loadErrors = useCallback(() => {
    setErrorsLoading(true)
    return fetchMetadataErrors()
      .then(setMetadataErrors)
      .catch(console.error)
      .finally(() => setErrorsLoading(false))
  }, [])

  function loadProviders() {
    setProvidersLoading(true)
    return fetchProviders()
      .then((data) => {
        setProviders(data)
        const saved = getSelectedStreamers()
        if (saved === null) {
          setSelectedIds(data.map((p) => p.provider_id))
        } else {
          setSelectedIds(saved)
        }
      })
      .catch(console.error)
      .finally(() => setProvidersLoading(false))
  }

  useEffect(() => {
    loadProviders()
    loadErrors()
    loadAppSettings()
    refreshStatus()
  }, [loadErrors, loadAppSettings, refreshStatus])

  const jobActive = isJobActive(status)

  useEffect(() => {
    if (wasJobActive.current && !jobActive) {
      onImport?.()
      loadProviders()
      loadErrors()
    }
    wasJobActive.current = jobActive
  }, [jobActive, onImport, loadErrors])

  const allProviderIds = providers.map((p) => p.provider_id)
  const searchTerm = providerSearch.trim().toLowerCase()
  const filteredProviders = searchTerm
    ? providers.filter((p) => p.provider_name.toLowerCase().includes(searchTerm))
    : providers

  function toggleProvider(id) {
    const next = selectedIds.includes(id)
      ? selectedIds.filter((pid) => pid !== id)
      : [...selectedIds, id]
    setSelectedIds(next)
    setSelectedStreamers(next, allProviderIds)
  }

  function selectAllProviders() {
    setSelectedIds(allProviderIds)
    setSelectedStreamers(allProviderIds, allProviderIds)
  }

  function clearAllProviders() {
    setSelectedIds([])
    setSelectedStreamers([], allProviderIds)
  }

  async function handleRefreshProviders() {
    setError(null)
    setRefreshingProviders(true)
    try {
      const result = await refreshProviders()
      if (result.queued) {
        await refreshStatus()
      } else {
        alert('No titles with TMDB data found to refresh.')
      }
    } catch (err) {
      setError(err.message || 'Failed to refresh streaming services')
    } finally {
      setRefreshingProviders(false)
    }
  }

  async function handleRefreshMetadata() {
    setError(null)
    setRefreshingMetadata(true)
    try {
      const result = await refreshMetadata()
      if (result.queued) {
        await refreshStatus()
      } else {
        alert('No titles in collection to rescan.')
      }
    } catch (err) {
      setError(err.message || 'Failed to start metadata rescan')
    } finally {
      setRefreshingMetadata(false)
    }
  }

  async function handleRetry(mediaId) {
    setError(null)
    try {
      await retryMetadata(mediaId)
      await refreshStatus()
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleDismiss(mediaId) {
    setError(null)
    try {
      await resolveMetadataError(mediaId, { notes: 'Dismissed manually' })
      loadErrors()
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleFixSearch(errItem) {
    setFixingId(errItem.media_id)
    setError(null)
    try {
      const results = await searchTmdb(errItem.title, errItem.media_type, errItem.year)
      setFixResults((prev) => ({ ...prev, [errItem.media_id]: results }))
    } catch (e) {
      setError(e.message)
    } finally {
      setFixingId(null)
    }
  }

  async function handleFixPick(mediaId, tmdbId) {
    setError(null)
    try {
      await resolveMetadataError(mediaId, { tmdbId, notes: 'Matched manually via TMDB search' })
      setFixResults((prev) => {
        const next = { ...prev }
        delete next[mediaId]
        return next
      })
      loadErrors()
      onImport?.()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleSaveTmdb(e) {
    e.preventDefault()
    setError(null)
    setSavingTmdb(true)
    try {
      const payload = { tmdbRegion: tmdbRegionInput.trim().toUpperCase() }
      if (tmdbKeyInput.trim()) {
        payload.tmdbApiKey = tmdbKeyInput.trim()
      }
      const result = await updateAppSettings(payload)
      setAppSettings(result)
      setTmdbKeyInput('')
      if (result.metadata_queued) {
        setStatus({
          running: true,
          total: result.metadata_total,
          completed: 0,
          failed: 0,
          job_type: 'metadata_import',
        })
        alert(
          `TMDB settings saved. Fetching metadata for ${result.metadata_total} titles in the background.`,
        )
      }
    } catch (err) {
      setError(err.message || 'Failed to save TMDB settings')
    } finally {
      setSavingTmdb(false)
    }
  }

  async function handleClearTmdbKey() {
    if (!window.confirm('Remove the saved TMDB API key? Metadata fetching will stop unless a key is set in the environment.')) {
      return
    }
    setError(null)
    setSavingTmdb(true)
    try {
      const result = await updateAppSettings({ tmdbApiKey: '', queuePendingMetadata: false })
      setAppSettings(result)
      setTmdbKeyInput('')
    } catch (err) {
      setError(err.message || 'Failed to clear TMDB key')
    } finally {
      setSavingTmdb(false)
    }
  }

  async function handleExport() {
    setError(null)
    const data = await exportCollection()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `movie-reel-export-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function handleDeleteCollection() {
    setError(null)
    setDeletingCollection(true)
    try {
      const result = await deleteCollection()
      setShowDeleteDialog(false)
      setProviders([])
      setSelectedIds([])
      setMetadataErrors([])
      setFixResults({})
      await refreshStatus()
      onImport?.()
      alert(
        result.deleted > 0
          ? `Removed ${result.deleted} titles from your collection.`
          : 'Your collection was already empty.',
      )
    } catch (err) {
      setError(err.message || 'Failed to delete collection')
    } finally {
      setDeletingCollection(false)
    }
  }

  async function handleImport(e) {
    const file = e.target.files?.[0]
    if (!file) return

    setImporting(true)
    setError(null)
    fileRef.current.value = ''

    try {
      const text = await file.text()
      const data = JSON.parse(text)
      const items = normalizeImportItems(data)
      const result = await importStubs(items, true)
      if (result.metadata_queued) {
        setStatus({
          running: true,
          total: result.metadata_total,
          completed: 0,
          failed: 0,
          job_type: 'metadata_import',
        })
        alert(
          `Imported ${result.imported} titles. Fetching metadata in the background — this may take a while.`,
        )
      } else {
        const msg = result.imported > 0
          ? `Imported ${result.imported} titles.`
          : `Imported ${result.imported} items successfully.`
        if (!result.metadata_queued && result.imported > 0) {
          alert(
            `${msg} Add a TMDB API key in Settings to fetch metadata.`,
          )
        } else {
          alert(msg)
        }
        onImport?.()
      }
    } catch (err) {
      setError(err.message || 'Import failed')
    } finally {
      setImporting(false)
    }
  }

  const jobLabel = status?.label || JOB_LABELS[status?.job_type] || 'Background job'

  return (
    <div style={{ maxWidth: 700 }}>
      <h1 className="page-title">Settings</h1>

      {error && <p className="settings-error">{error}</p>}

      <div className="section">
        <h2>TMDB API</h2>
        <p className="overview" style={{ marginBottom: '1rem' }}>
          Metadata, posters, cast, and streaming availability come from{' '}
          <a href="https://www.themoviedb.org/settings/api" target="_blank" rel="noreferrer">
            TMDB
          </a>
          . Set your API key here — no server restart or <code>.env</code> file required.
        </p>
        {appSettings && (
          <p className="overview tmdb-status" style={{ marginBottom: '1rem', fontSize: '0.85rem' }}>
            Status:{' '}
            <span className={appSettings.tmdb_configured ? 'tmdb-status__ok' : 'tmdb-status__missing'}>
              {appSettings.tmdb_configured ? 'Configured' : 'Not configured'}
            </span>
            {appSettings.tmdb_api_key_preview && (
              <> · Key: {appSettings.tmdb_api_key_preview}</>
            )}
            {appSettings.tmdb_key_source === 'environment' && (
              <> · Using key from environment variable</>
            )}
          </p>
        )}
        <form className="tmdb-settings-form" onSubmit={handleSaveTmdb}>
          <label className="tmdb-settings-form__field">
            <span>API key</span>
            <input
              type="password"
              className="search-input"
              value={tmdbKeyInput}
              onChange={(e) => setTmdbKeyInput(e.target.value)}
              placeholder={appSettings?.tmdb_configured ? 'Enter new key to replace' : 'Paste your TMDB API key'}
              autoComplete="off"
            />
          </label>
          <label className="tmdb-settings-form__field">
            <span>Region</span>
            <input
              type="text"
              className="search-input tmdb-settings-form__region"
              value={tmdbRegionInput}
              onChange={(e) => setTmdbRegionInput(e.target.value.toUpperCase())}
              placeholder="US"
              maxLength={2}
            />
          </label>
          <div className="tmdb-settings-form__actions">
            <button type="submit" className="btn-primary" disabled={savingTmdb}>
              {savingTmdb ? 'Saving…' : 'Save TMDB settings'}
            </button>
            {appSettings?.tmdb_key_source === 'database' && appSettings.tmdb_configured && (
              <button type="button" className="job-actions__btn" disabled={savingTmdb} onClick={handleClearTmdbKey}>
                Remove saved key
              </button>
            )}
          </div>
        </form>
      </div>

      {isJobActive(status) && (
        <div className="settings-panel">
          <h2>{jobLabel}</h2>
          {status.running ? (
            <>
              <p className="overview">
                {status.completed} / {status.total} complete
                {status.failed > 0 && ` (${status.failed} failed)`}
              </p>
              {status.current_item && (
                <p className="overview" style={{ fontSize: '0.85rem' }}>
                  Current: {status.current_item}
                </p>
              )}
            </>
          ) : (
            <p className="overview">Queued — waiting for other jobs to finish</p>
          )}
          {status.queue?.queued?.length > 0 && (
            <p className="overview" style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
              {status.queue.queued.length} more job(s) in queue
            </p>
          )}
          {status.schedule?.enabled && (
            <p className="overview" style={{ fontSize: '0.85rem', marginTop: '0.75rem' }}>
              Daily schedule: providers at {String(status.schedule.provider_refresh_hour).padStart(2, '0')}:00,
              metadata rescan at {String(status.schedule.metadata_rescan_hour).padStart(2, '0')}:00
            </p>
          )}
        </div>
      )}

      {!isJobActive(status) && status?.last_provider_refresh && (
        <p className="overview" style={{ marginBottom: '1rem', fontSize: '0.85rem' }}>
          Last provider refresh: {new Date(status.last_provider_refresh).toLocaleString()}
          {status.last_metadata_rescan && (
            <> · Last metadata rescan: {new Date(status.last_metadata_rescan).toLocaleString()}</>
          )}
        </p>
      )}

      {metadataErrors.length > 0 && (
        <div className="section">
          <h2>Metadata errors ({metadataErrors.length})</h2>
          <p className="overview" style={{ marginBottom: '1rem' }}>
            Titles that failed to match or fetch from TMDB. Retry, pick the correct match, or dismiss.
          </p>
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
                <p className="error-list__date">
                  {new Date(err.created_at).toLocaleString()}
                </p>
                <div className="error-list__actions">
                  <button type="button" onClick={() => handleRetry(err.media_id)}>
                    Retry
                  </button>
                  <button
                    type="button"
                    onClick={() => handleFixSearch(err)}
                    disabled={fixingId === err.media_id}
                  >
                    {fixingId === err.media_id ? 'Searching…' : 'Find match'}
                  </button>
                  <button type="button" onClick={() => handleDismiss(err.media_id)}>
                    Dismiss
                  </button>
                </div>
                {fixResults[err.media_id]?.length > 0 && (
                  <div className="error-list__matches">
                    {fixResults[err.media_id].map((match) => (
                      <button
                        key={match.tmdb_id}
                        type="button"
                        className="error-list__match"
                        onClick={() => handleFixPick(err.media_id, match.tmdb_id)}
                      >
                        {match.poster_url && (
                          <img src={match.poster_url} alt="" />
                        )}
                        <span>
                          {match.title}
                          {match.year ? ` (${match.year})` : ''}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!errorsLoading && metadataErrors.length === 0 && (
        <p className="overview" style={{ marginBottom: '1.5rem', fontSize: '0.85rem' }}>
          No metadata errors.
        </p>
      )}

      <div className="section">
        <h2>Background jobs</h2>
        <p className="overview" style={{ marginBottom: '1rem' }}>
          Providers refresh daily so streaming availability stays current. Metadata rescans run overnight
          one title at a time to respect TMDB rate limits.
        </p>
        <div className="job-actions">
          <button
            type="button"
            onClick={handleRefreshProviders}
            disabled={refreshingProviders}
            className="job-actions__btn"
          >
            {refreshingProviders ? 'Queueing…' : 'Refresh streaming data now'}
          </button>
          <button
            type="button"
            onClick={handleRefreshMetadata}
            disabled={refreshingMetadata}
            className="job-actions__btn"
          >
            {refreshingMetadata ? 'Queueing…' : 'Rescan metadata now'}
          </button>
        </div>
      </div>

      <div className="section">
        <h2>Streaming services</h2>
        <p className="overview" style={{ marginBottom: '1rem' }}>
          Choose which services you use — subscriptions, free and ad-supported platforms, and rental or purchase options.
          Title pages and browse will only show matches on your selected services.
        </p>
        {providersLoading ? (
          <p className="overview">Loading services…</p>
        ) : providers.length === 0 ? (
          <p className="overview">No streaming services found in your collection yet.</p>
        ) : (
          <>
            <div className="streamer-actions">
              <button type="button" onClick={selectAllProviders}>Select all</button>
              <button type="button" onClick={clearAllProviders}>Clear all</button>
            </div>
            <input
              type="search"
              className="search-input streamer-search"
              placeholder="Search providers…"
              value={providerSearch}
              onChange={(e) => setProviderSearch(e.target.value)}
            />
            <div className="streamer-list">
              {filteredProviders.length === 0 ? (
                <p className="overview">No providers match your search.</p>
              ) : (
                filteredProviders.map((p) => {
                  const checked = selectedIds.includes(p.provider_id)
                  return (
                    <label
                      key={p.provider_id}
                      className={`streamer-option${checked ? ' streamer-option--selected' : ''}`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleProvider(p.provider_id)}
                      />
                      {p.logo_url ? (
                        <img src={p.logo_url} alt="" className="streamer-option__logo" />
                      ) : (
                        <span className="streamer-option__logo streamer-option__logo--placeholder">📺</span>
                      )}
                      <span className="streamer-option__name">{p.provider_name}</span>
                    </label>
                  )
                })
              )}
            </div>
          </>
        )}
      </div>

      <div className="section">
        <h2>Export collection</h2>
        <p className="overview" style={{ marginBottom: '1rem' }}>
          Download your collection as a compact JSON file (titles, years, seasons, and tags).
          Use this to back up or transfer to another instance.
        </p>
        <button
          onClick={handleExport}
          className="btn-primary"
        >
          Export JSON
        </button>
      </div>

      <div className="section">
        <h2>Import collection</h2>
        <p className="overview" style={{ marginBottom: '1rem' }}>
          Import a JSON export file. Titles are matched and metadata is fetched from TMDB in the background.
          Existing titles are updated, not duplicated.
        </p>
        <input
          ref={fileRef}
          type="file"
          accept=".json"
          onChange={handleImport}
          disabled={importing}
          className="import-file-input"
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={importing}
          className="btn-primary"
        >
          {importing ? 'Importing…' : 'Import JSON'}
        </button>
      </div>

      <div className="section danger-zone">
        <h2>Delete collection</h2>
        <p className="overview" style={{ marginBottom: '1rem' }}>
          Permanently remove every title, tag, and streaming link from your library.
          TMDB settings are kept. Export first if you want a backup.
        </p>
        <button
          type="button"
          className="btn-danger"
          onClick={() => setShowDeleteDialog(true)}
        >
          Delete entire collection
        </button>
      </div>

      <ConfirmDialog
        open={showDeleteDialog}
        title="Delete entire collection?"
        message="This permanently removes all movies and TV shows, cast links, genres, tags, and streaming data. This cannot be undone."
        confirmLabel="Delete collection"
        cancelLabel="Keep collection"
        danger
        loading={deletingCollection}
        onConfirm={handleDeleteCollection}
        onCancel={() => !deletingCollection && setShowDeleteDialog(false)}
      />
    </div>
  )
}
