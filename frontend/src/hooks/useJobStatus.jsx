import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { fetchImportStatus } from '../api'

export function isJobActive(status) {
  if (!status) return false
  if (status.running) return true
  return Boolean(status.queue?.queued?.length)
}

const JobStatusContext = createContext(null)

export function JobStatusProvider({ children, onJobComplete }) {
  const [status, setStatus] = useState(null)

  const refreshStatus = useCallback(
    () =>
      fetchImportStatus()
        .then((next) => {
          setStatus(next)
          return next
        })
        .catch((err) => {
          console.error(err)
          return null
        }),
    [],
  )

  useEffect(() => {
    refreshStatus()
  }, [refreshStatus])

  useEffect(() => {
    if (!isJobActive(status)) return undefined

    const interval = setInterval(async () => {
      const next = await fetchImportStatus()
      setStatus(next)
      if (!isJobActive(next)) {
        onJobComplete?.()
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [status, onJobComplete])

  return (
    <JobStatusContext.Provider value={{ status, setStatus, refreshStatus }}>
      {children}
    </JobStatusContext.Provider>
  )
}

export function useJobStatus() {
  const context = useContext(JobStatusContext)
  if (!context) {
    throw new Error('useJobStatus must be used within JobStatusProvider')
  }
  return context
}
