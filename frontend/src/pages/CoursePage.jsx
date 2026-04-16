import { useCallback, useEffect, useRef, useState } from 'react'
import { Navigate, useLocation, useNavigate, useParams } from 'react-router-dom'
import { fetchAuthSession, getCurrentUser } from 'aws-amplify/auth'
import './CoursePage.css'
import { useLanguageControl } from '../language-control/LanguageControlProvider.jsx'
import { getCourseDocuments, getUploadUrl, uploadFileToS3 } from '../services/documentsService.js'

function fileKey(file) {
  return `${file.name}-${file.size}-${file.lastModified}`
}

function mergeFileLists(prev, incoming) {
  const map = new Map()
  for (const f of prev) map.set(fileKey(f), f)
  for (const f of incoming) map.set(fileKey(f), f)
  return Array.from(map.values())
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / k ** i).toFixed(i > 0 ? 1 : 0))} ${sizes[i]}`
}

function formatDocumentDate(iso, lang) {
  if (!iso || typeof iso !== 'string') return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString(lang === 'he' ? 'he-IL' : 'en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export default function CoursePage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { courseId: courseIdParam } = useParams()
  const { t, lang, setLang, dir, tx } = useLanguageControl()
  const [authStatus, setAuthStatus] = useState('loading')
  const [activeTab, setActiveTab] = useState('materials')
  const [documents, setDocuments] = useState([])
  const [documentsLoading, setDocumentsLoading] = useState(false)
  const [documentsError, setDocumentsError] = useState(null)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState([])
  const [isDraggingOverDropzone, setIsDraggingOverDropzone] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(null)
  const [uploadError, setUploadError] = useState(null)
  const [uploadSuccess, setUploadSuccess] = useState(false)
  const fileInputRef = useRef(null)
  const dragDepthRef = useRef(0)

  const courseNameFromState =
    typeof location.state?.courseName === 'string' ? location.state.courseName.trim() : ''

  const displayCourseName = courseNameFromState || t.home.untitledCourse
  const courseId = courseIdParam?.trim() ?? ''

  const loadDocuments = useCallback(async () => {
    if (!courseId) return
    setDocumentsLoading(true)
    setDocumentsError(null)
    try {
      const session = await fetchAuthSession()
      const idToken = session.tokens?.idToken?.toString()
      if (!idToken) {
        setDocuments([])
        setDocumentsError(t.coursePage.uploadMissingSession)
        return
      }
      const list = await getCourseDocuments(courseId, idToken)
      setDocuments(list)
    } catch (err) {
      let message = t.coursePage.documentsError
      const apiMsg = err?.response?.data?.message
      if (typeof apiMsg === 'string' && apiMsg.trim()) {
        message = apiMsg.trim()
      } else if (typeof err?.message === 'string' && err.message.includes('VITE_API_URL')) {
        message = t.coursePage.uploadApiNotConfigured
      }
      setDocumentsError(message)
      setDocuments([])
    } finally {
      setDocumentsLoading(false)
    }
  }, [courseId, t])

  useEffect(() => {
    if (authStatus !== 'authed' || !courseId || activeTab !== 'materials') return
    loadDocuments()
  }, [authStatus, courseId, activeTab, loadDocuments])

  const closeUploadModal = useCallback(() => {
    dragDepthRef.current = 0
    setIsDraggingOverDropzone(false)
    setSelectedFiles([])
    setIsUploadModalOpen(false)
    setIsUploading(false)
    setUploadProgress(null)
    setUploadError(null)
    setUploadSuccess(false)
  }, [])

  const addFiles = useCallback((files) => {
    if (!files.length) return
    setSelectedFiles((prev) => mergeFileLists(prev, files))
  }, [])

  const removeFileAt = useCallback((index) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const handleUploadModalSubmit = useCallback(async () => {
    if (selectedFiles.length === 0 || isUploading) return
    if (!courseId) {
      setUploadError(t.coursePage.uploadMissingCourseId)
      return
    }

    setUploadError(null)
    setUploadSuccess(false)
    setIsUploading(true)
    const filesSnapshot = [...selectedFiles]
    const total = filesSnapshot.length
    setUploadProgress({ current: 0, total })

    try {
      const session = await fetchAuthSession()
      const idToken = session.tokens?.idToken?.toString()
      if (!idToken) {
        setUploadError(t.coursePage.uploadMissingSession)
        return
      }

      for (let i = 0; i < total; i++) {
        const file = filesSnapshot[i]
        setUploadProgress({ current: i + 1, total })
        const fileType = file.type || 'application/octet-stream'
        const { upload_url: uploadUrl } = await getUploadUrl(courseId, file.name, fileType, idToken)
        await uploadFileToS3(uploadUrl, file, fileType)
      }

      setSelectedFiles([])
      await loadDocuments()
      setUploadSuccess(true)
    } catch (err) {
      let message = t.coursePage.uploadError
      const apiMsg = err?.response?.data?.message
      if (typeof apiMsg === 'string' && apiMsg.trim()) {
        message = apiMsg.trim()
      } else if (typeof err?.message === 'string' && err.message.includes('VITE_API_URL')) {
        message = t.coursePage.uploadApiNotConfigured
      } else if (typeof err?.message === 'string' && err.message.trim()) {
        message = err.message.trim()
      }
      setUploadError(message)
    } finally {
      setIsUploading(false)
      setUploadProgress(null)
    }
  }, [courseId, isUploading, loadDocuments, selectedFiles, t])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        await getCurrentUser()
        if (!cancelled) setAuthStatus('authed')
      } catch {
        if (!cancelled) setAuthStatus('guest')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!isUploadModalOpen) return undefined
    const onKeyDown = (e) => {
      if (e.key === 'Escape' && !isUploading) closeUploadModal()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [isUploadModalOpen, isUploading, closeUploadModal])

  useEffect(() => {
    if (!uploadSuccess || !isUploadModalOpen) return undefined
    const timer = window.setTimeout(() => {
      closeUploadModal()
    }, 2200)
    return () => window.clearTimeout(timer)
  }, [uploadSuccess, isUploadModalOpen, closeUploadModal])

  if (authStatus === 'loading') {
    return (
      <main className="course-page" dir={dir} lang={lang}>
        <section className="course-page__loading">
          <p className="course-page__loading-text">{t.coursePage.loading}</p>
        </section>
      </main>
    )
  }

  if (authStatus === 'guest') {
    return <Navigate to="/" replace />
  }

  const materialsCount = documents.length
  const showDocList = !documentsLoading && !documentsError && documents.length > 0
  const showDocEmpty = !documentsLoading && !documentsError && documents.length === 0

  return (
    <main className="course-page" dir={dir} lang={lang}>
      <div className="course-page__top-bar">
        <button
          type="button"
          className="course-page__back-btn"
          onClick={() => navigate('/home')}
        >
          {t.coursePage.backToDashboard}
        </button>
        <div className="course-page__lang-switch" role="group" aria-label={t.common.switchLanguage}>
          <button
            type="button"
            className={`course-page__lang-btn ${lang === 'he' ? 'course-page__lang-btn--active' : ''}`}
            onClick={() => setLang('he')}
          >
            {t.common.langHe}
          </button>
          <button
            type="button"
            className={`course-page__lang-btn ${lang === 'en' ? 'course-page__lang-btn--active' : ''}`}
            onClick={() => setLang('en')}
          >
            {t.common.langEn}
          </button>
        </div>
      </div>

      <header className="course-page__banner">
        <div className="course-page__banner-inner">
          <h1 className="course-page__title">{displayCourseName}</h1>
          <p className="course-page__materials-stat" aria-live="polite">
            {tx(t.coursePage.materialsCountStat, { count: materialsCount })}
          </p>
        </div>
      </header>

      <div className="course-page__body">
        <nav
          className="course-page__inner-sidebar"
          aria-label={t.coursePage.courseInnerNavAria}
        >
          <div className="course-page__inner-nav">
            <button
              type="button"
              className={`course-page__inner-nav-item ${
                activeTab === 'materials' ? 'course-page__inner-nav-item--active' : ''
              }`}
              onClick={() => setActiveTab('materials')}
              aria-current={activeTab === 'materials' ? 'page' : undefined}
            >
              {t.coursePage.tabMaterials}
            </button>
          </div>
        </nav>

        <div className="course-page__main">
          {activeTab === 'materials' ? (
            <section aria-label={t.coursePage.materialsSectionLabel}>
              <div className="course-page__materials-header">
                <h2 className="course-page__materials-heading course-page__materials-heading--panel">
                  {t.coursePage.materialsHeading}
                </h2>
                <button
                  type="button"
                  className="course-page__upload-btn"
                  onClick={() => {
                    setUploadError(null)
                    setUploadSuccess(false)
                    setIsUploadModalOpen(true)
                  }}
                >
                  {t.coursePage.uploadMaterial}
                </button>
              </div>

              {documentsLoading ? (
                <div className="course-page__documents-skeleton" aria-busy="true">
                  <div className="course-page__documents-skeleton-row" />
                  <div className="course-page__documents-skeleton-row" />
                  <div className="course-page__documents-skeleton-row" />
                  <p className="course-page__documents-state">{t.coursePage.documentsLoading}</p>
                </div>
              ) : null}

              {documentsError && !documentsLoading ? (
                <p className="course-page__documents-error" role="alert">
                  {documentsError}
                </p>
              ) : null}

              {showDocEmpty ? (
                <p className="course-page__materials-empty">{t.coursePage.documentsListEmpty}</p>
              ) : null}

              {showDocList ? (
                <ul
                  className="course-page__doc-list"
                  aria-label={t.coursePage.documentsListAriaLabel}
                >
                  {documents.map((doc, index) => {
                    const id = doc.document_id ?? doc.documentId ?? `doc-${index}`
                    const name = doc.original_file_name ?? doc.originalFileName ?? '—'
                    const created = doc.created_at ?? doc.createdAt
                    const status = doc.processing_status ?? doc.processingStatus ?? ''
                    const statusLabel =
                      String(status).toUpperCase() === 'UPLOADED'
                        ? t.coursePage.statusUploaded
                        : String(status || '—')
                    return (
                      <li key={String(id)} className="course-page__doc-card">
                        <div className="course-page__doc-card-main">
                          <span className="course-page__doc-card-name" title={String(name)}>
                            {String(name)}
                          </span>
                          <span className="course-page__doc-card-date">
                            {formatDocumentDate(created, lang)}
                          </span>
                        </div>
                        <span className="course-page__doc-badge">{statusLabel}</span>
                      </li>
                    )
                  })}
                </ul>
              ) : null}
            </section>
          ) : null}
        </div>
      </div>

      {isUploadModalOpen ? (
        <div
          className="course-page__modal-backdrop"
          role="presentation"
          onClick={() => {
            if (!isUploading) closeUploadModal()
          }}
        >
          <section
            className="course-page__modal course-page__modal--upload"
            role="dialog"
            aria-modal="true"
            aria-labelledby="course-upload-modal-title"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="course-upload-modal-title" className="course-page__modal-title">
              {t.coursePage.uploadModalTitle}
            </h2>
            <p className="course-page__modal-subtitle">{t.coursePage.uploadModalSubtitle}</p>

            {uploadSuccess ? (
              <p className="course-page__upload-feedback course-page__upload-feedback--success" role="status">
                {t.coursePage.uploadSuccess}
              </p>
            ) : null}

            {uploadError ? (
              <p className="course-page__upload-feedback course-page__upload-feedback--error" role="alert">
                {uploadError}
              </p>
            ) : null}

            {isUploading && uploadProgress ? (
              <p className="course-page__upload-feedback course-page__upload-feedback--progress" aria-live="polite">
                {tx(t.coursePage.uploadProgress, {
                  current: uploadProgress.current,
                  total: uploadProgress.total,
                })}
              </p>
            ) : null}

            {!uploadSuccess ? (
              <>
                <input
                  ref={fileInputRef}
                  type="file"
                  className="course-page__upload-input"
                  multiple
                  tabIndex={-1}
                  disabled={isUploading}
                  onChange={(e) => {
                    const { files } = e.target
                    if (files?.length) addFiles(Array.from(files))
                    e.target.value = ''
                  }}
                />

                <div
                  className={`course-page__upload-dropzone ${
                    isDraggingOverDropzone ? 'course-page__upload-dropzone--active' : ''
                  } ${isUploading ? 'course-page__upload-dropzone--disabled' : ''}`}
                  role="button"
                  tabIndex={isUploading ? -1 : 0}
                  aria-disabled={isUploading}
                  aria-label={t.coursePage.uploadDropHint}
                  onClick={() => {
                    if (!isUploading) fileInputRef.current?.click()
                  }}
                  onKeyDown={(e) => {
                    if (isUploading) return
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      fileInputRef.current?.click()
                    }
                  }}
                  onDragEnter={(e) => {
                    if (isUploading) return
                    e.preventDefault()
                    e.stopPropagation()
                    dragDepthRef.current += 1
                    setIsDraggingOverDropzone(true)
                  }}
                  onDragOver={(e) => {
                    if (isUploading) return
                    e.preventDefault()
                    e.stopPropagation()
                  }}
                  onDragLeave={(e) => {
                    if (isUploading) return
                    e.preventDefault()
                    e.stopPropagation()
                    dragDepthRef.current -= 1
                    if (dragDepthRef.current <= 0) {
                      dragDepthRef.current = 0
                      setIsDraggingOverDropzone(false)
                    }
                  }}
                  onDrop={(e) => {
                    if (isUploading) return
                    e.preventDefault()
                    e.stopPropagation()
                    dragDepthRef.current = 0
                    setIsDraggingOverDropzone(false)
                    const dropped = Array.from(e.dataTransfer?.files || [])
                    addFiles(dropped)
                  }}
                >
                  <span className="course-page__upload-dropzone-icon" aria-hidden>
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                      <path
                        d="M12 4v12m0 0l-4-4m4 4l4-4M5 20h14"
                        stroke="currentColor"
                        strokeWidth="1.75"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                  <p className="course-page__upload-dropzone-hint">{t.coursePage.uploadDropHint}</p>
                </div>

                {selectedFiles.length > 0 ? (
                  <div className="course-page__upload-files">
                    <p className="course-page__upload-files-label">{t.coursePage.uploadSelectedHeading}</p>
                    <ul className="course-page__upload-files-list">
                      {selectedFiles.map((file, index) => (
                        <li key={fileKey(file)} className="course-page__upload-files-item">
                          <span className="course-page__upload-files-name" title={file.name}>
                            {file.name}
                          </span>
                          <span className="course-page__upload-files-size">{formatFileSize(file.size)}</span>
                          <button
                            type="button"
                            className="course-page__upload-files-remove"
                            disabled={isUploading}
                            onClick={(e) => {
                              e.stopPropagation()
                              removeFileAt(index)
                            }}
                            aria-label={tx(t.coursePage.uploadRemoveFileAria, { name: file.name })}
                          >
                            ×
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </>
            ) : null}

            <div className="course-page__modal-actions">
              <button
                type="button"
                className="course-page__modal-cancel"
                disabled={isUploading}
                onClick={closeUploadModal}
              >
                {t.home.cancel}
              </button>
              {!uploadSuccess ? (
                <button
                  type="button"
                  className="course-page__modal-submit"
                  disabled={selectedFiles.length === 0 || isUploading}
                  onClick={handleUploadModalSubmit}
                >
                  {isUploading ? t.coursePage.uploadUploading : t.coursePage.uploadSubmit}
                </button>
              ) : null}
            </div>
          </section>
        </div>
      ) : null}
    </main>
  )
}
