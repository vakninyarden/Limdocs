import { useCallback, useEffect, useRef, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { getCurrentUser } from 'aws-amplify/auth'
import './CoursePage.css'
import { useLanguageControl } from '../language-control/LanguageControlProvider.jsx'

const MOCK_MATERIALS_COUNT = 1

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

export default function CoursePage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { t, lang, setLang, dir, tx } = useLanguageControl()
  const [authStatus, setAuthStatus] = useState('loading')
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState([])
  const [isDraggingOverDropzone, setIsDraggingOverDropzone] = useState(false)
  const fileInputRef = useRef(null)
  const dragDepthRef = useRef(0)

  const courseNameFromState =
    typeof location.state?.courseName === 'string' ? location.state.courseName.trim() : ''

  const displayCourseName = courseNameFromState || t.home.untitledCourse

  const closeUploadModal = useCallback(() => {
    dragDepthRef.current = 0
    setIsDraggingOverDropzone(false)
    setSelectedFiles([])
    setIsUploadModalOpen(false)
  }, [])

  const addFiles = useCallback((files) => {
    if (!files.length) return
    setSelectedFiles((prev) => mergeFileLists(prev, files))
  }, [])

  const removeFileAt = useCallback((index) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const handleUploadModalSubmit = useCallback(() => {
    if (selectedFiles.length === 0) return
    closeUploadModal()
  }, [selectedFiles.length, closeUploadModal])

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
      if (e.key === 'Escape') closeUploadModal()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [isUploadModalOpen, closeUploadModal])

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
            {tx(t.coursePage.materialsCountStat, { count: MOCK_MATERIALS_COUNT })}
          </p>
        </div>
      </header>

      <div className="course-page__toolbar">
        <button
          type="button"
          className="course-page__upload-btn"
          onClick={() => setIsUploadModalOpen(true)}
        >
          {t.coursePage.uploadMaterial}
        </button>
      </div>

      <section className="course-page__materials-section" aria-label={t.coursePage.materialsSectionLabel}>
        <h2 className="course-page__materials-heading">{t.coursePage.materialsHeading}</h2>
        <p className="course-page__materials-empty">{t.coursePage.materialsEmpty}</p>
      </section>

      {isUploadModalOpen ? (
        <div
          className="course-page__modal-backdrop"
          role="presentation"
          onClick={closeUploadModal}
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

            <input
              ref={fileInputRef}
              type="file"
              className="course-page__upload-input"
              multiple
              tabIndex={-1}
              onChange={(e) => {
                const { files } = e.target
                if (files?.length) addFiles(Array.from(files))
                e.target.value = ''
              }}
            />

            <div
              className={`course-page__upload-dropzone ${
                isDraggingOverDropzone ? 'course-page__upload-dropzone--active' : ''
              }`}
              role="button"
              tabIndex={0}
              aria-label={t.coursePage.uploadDropHint}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  fileInputRef.current?.click()
                }
              }}
              onDragEnter={(e) => {
                e.preventDefault()
                e.stopPropagation()
                dragDepthRef.current += 1
                setIsDraggingOverDropzone(true)
              }}
              onDragOver={(e) => {
                e.preventDefault()
                e.stopPropagation()
              }}
              onDragLeave={(e) => {
                e.preventDefault()
                e.stopPropagation()
                dragDepthRef.current -= 1
                if (dragDepthRef.current <= 0) {
                  dragDepthRef.current = 0
                  setIsDraggingOverDropzone(false)
                }
              }}
              onDrop={(e) => {
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

            <div className="course-page__modal-actions">
              <button type="button" className="course-page__modal-cancel" onClick={closeUploadModal}>
                {t.home.cancel}
              </button>
              <button
                type="button"
                className="course-page__modal-submit"
                disabled={selectedFiles.length === 0}
                onClick={handleUploadModalSubmit}
              >
                {t.coursePage.uploadSubmit}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  )
}
