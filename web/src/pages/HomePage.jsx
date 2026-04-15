import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import {
  fetchUserAttributes,
  fetchAuthSession,
  getCurrentUser,
  signOut,
} from 'aws-amplify/auth'
import './HomePage.css'
import { useLanguageControl } from '../language-control/LanguageControlProvider.jsx'
import { getUserCourses } from '../services/coursesService.js'

function IconHome() {
  return (
    <svg className="home-page__nav-icon" width="20" height="20" viewBox="0 0 24 24" aria-hidden>
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 10.25 12 3l9 7.25V20a.75.75 0 01-.75.75h-4.5v-6h-3v6H3.75A.75.75 0 013 20v-9.75z"
      />
    </svg>
  )
}

function IconBooks() {
  return (
    <svg className="home-page__nav-icon" width="20" height="20" viewBox="0 0 24 24" aria-hidden>
      <circle cx="4" cy="6" r="1.25" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="4" cy="12" r="1.25" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="4" cy="18" r="1.25" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        d="M8 6h13M8 12h13M8 18h10"
      />
    </svg>
  )
}

function IconUser() {
  return (
    <svg className="home-page__nav-icon" width="20" height="20" viewBox="0 0 24 24" aria-hidden>
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"
      />
      <circle cx="12" cy="7" r="4" fill="none" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  )
}

function IconLogout() {
  return (
    <svg className="home-page__nav-icon" width="20" height="20" viewBox="0 0 24 24" aria-hidden>
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M15 12H4m11 0l-3-3m3 3l-3 3M8 5V4a1 1 0 011-1h9a1 1 0 011 1v16a1 1 0 01-1 1H9a1 1 0 01-1-1v-1"
      />
    </svg>
  )
}

function IconFolder() {
  return (
    <svg className="home-page__course-icon" width="22" height="22" viewBox="0 0 24 24" aria-hidden>
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 7.5V18a1.5 1.5 0 001.5 1.5h15A1.5 1.5 0 0021 18V9a1.5 1.5 0 00-1.5-1.5h-6.379a1.5 1.5 0 01-1.06-.439l-1.122-1.122A1.5 1.5 0 009.879 5.5H4.5A1.5 1.5 0 003 7v.5z"
      />
    </svg>
  )
}

function IconChevronEnd() {
  return (
    <svg
      className="home-page__course-chevron"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      aria-hidden
    >
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 6l6 6-6 6"
      />
    </svg>
  )
}

function IconPlus() {
  return (
    <svg
      className="home-page__course-icon home-page__course-icon--plus"
      width="22"
      height="22"
      viewBox="0 0 24 24"
      aria-hidden
    >
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        d="M12 5v14M5 12h14"
      />
    </svg>
  )
}

function logAuthError(context, error) {
  const message = error?.message ?? String(error)
  const name = error?.name ?? error?.code
  console.warn('[Auth i18n draft]', context, { name, message, error })
}

export default function HomePage() {
  const navigate = useNavigate()
  const { t, lang, setLang, dir, tx } = useLanguageControl()
  const [status, setStatus] = useState('loading')
  const [displayName, setDisplayName] = useState('')
  const [isCreateCourseOpen, setIsCreateCourseOpen] = useState(false)
  const [isCreatingCourse, setIsCreatingCourse] = useState(false)
  const [createCourseError, setCreateCourseError] = useState('')
  const [currentUserId, setCurrentUserId] = useState('')
  const [courses, setCourses] = useState([])
  const [isCoursesLoading, setIsCoursesLoading] = useState(false)
  const [coursesError, setCoursesError] = useState('')
  const [coursesRefreshKey, setCoursesRefreshKey] = useState(0)
  const apiBaseUrl = import.meta.env.VITE_API_URL ?? ''
  const [courseDraft, setCourseDraft] = useState({
    name: '',
    description: '',
    visibility: 'private',
  })

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const user = await getCurrentUser()
        let attrs = {}
        try {
          attrs = await fetchUserAttributes()
        } catch (attrErr) {
          logAuthError('fetchUserAttributes', attrErr)
        }
        if (cancelled) return
        const name =
          attrs.given_name ??
          attrs.name ??
          attrs.preferred_username ??
          user.username
        setCurrentUserId(String(user.userId ?? attrs.sub ?? '').trim())
        setDisplayName(String(name || user.username || '').trim() || 'Guest')
        setStatus('authed')
      } catch (e) {
        logAuthError('getCurrentUser / fetchUserAttributes', e)
        if (!cancelled) setStatus('guest')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (status !== 'authed' || !currentUserId) return

      try {
        setIsCoursesLoading(true)
        setCoursesError('')

        const session = await fetchAuthSession()
        const idToken = session.tokens?.idToken?.toString()
        if (!idToken) {
          throw new Error('Missing authentication token.')
        }

        const items = await getUserCourses(currentUserId, idToken)
        if (!cancelled) {
          setCourses(Array.isArray(items) ? items : [])
        }
      } catch (error) {
        console.error('[get-my-courses-failed]', error)
        if (!cancelled) {
          setCourses([])
          setCoursesError(error?.message || 'Could not load your courses.')
        }
      } finally {
        if (!cancelled) setIsCoursesLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [currentUserId, status, coursesRefreshKey])

  const handleLogout = async () => {
    try {
      await signOut()
    } catch (e) {
      logAuthError('signOut', e)
    }
    navigate('/', { replace: true })
  }

  const updateCourseDraft = (field, value) => {
    setCourseDraft((prev) => ({ ...prev, [field]: value }))
  }

  const closeCreateCourseModal = () => {
    setIsCreateCourseOpen(false)
    setCreateCourseError('')
    setCourseDraft({
      name: '',
      description: '',
      visibility: 'private',
    })
  }

  const handleCreateCourseSubmit = async (e) => {
    e.preventDefault()
    setCreateCourseError('')

    if (!apiBaseUrl) {
      setCreateCourseError('API is not configured. Set VITE_API_URL.')
      return
    }

    try {
      setIsCreatingCourse(true)
      const session = await fetchAuthSession()
      const accessToken = session.tokens?.idToken?.toString()

      if (!accessToken) {
        setCreateCourseError('You are not authenticated. Please sign in again.')
        return
      }

      const response = await fetch(`${apiBaseUrl}/courses`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          course_name: courseDraft.name.trim(),
          description: courseDraft.description.trim(),
          is_public: courseDraft.visibility === 'public',
        }),
      })

      const payload = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(payload?.message || `Failed with status ${response.status}`)
      }

      closeCreateCourseModal()
      setCoursesRefreshKey((prev) => prev + 1)
    } catch (error) {
      console.error('[create-course-failed]', error)
      setCreateCourseError(error?.message || 'Could not create course.')
    } finally {
      setIsCreatingCourse(false)
    }
  }

  if (status === 'loading') {
    return (
      <main className="home-page" dir={dir} lang={lang}>
        <section className="home-page__loading">
          <p className="home-page__greeting home-page__greeting--muted">{t.home.loading}</p>
        </section>
      </main>
    )
  }

  if (status === 'guest') {
    return <Navigate to="/" replace />
  }

  return (
    <main className="home-page" dir={dir} lang={lang}>
      <aside className="home-page__sidebar" aria-label={t.home.navLabel}>
        <div className="home-page__brand">
          <div className="home-page__logo" aria-hidden>
            L
          </div>
          <p className="home-page__brand-name">{t.home.brandName}</p>
        </div>

        <nav className="home-page__menu">
          <button type="button" className="home-page__menu-item home-page__menu-item--active">
            <IconHome />
            <span>{t.home.dashboard}</span>
          </button>
          <button type="button" className="home-page__menu-item">
            <IconBooks />
            <span>{t.home.myCourses}</span>
          </button>
          <button type="button" className="home-page__menu-item">
            <IconUser />
            <span>{t.home.profile}</span>
          </button>
        </nav>

        <button type="button" className="home-page__logout" onClick={handleLogout}>
          <IconLogout />
          <span>{t.home.logout}</span>
        </button>
      </aside>

      <section className="home-page__content">
        <div className="home-page__lang-switch" role="group" aria-label={t.common.switchLanguage}>
          <button
            type="button"
            className={`home-page__lang-btn ${lang === 'he' ? 'home-page__lang-btn--active' : ''}`}
            onClick={() => setLang('he')}
          >
            {t.common.langHe}
          </button>
          <button
            type="button"
            className={`home-page__lang-btn ${lang === 'en' ? 'home-page__lang-btn--active' : ''}`}
            onClick={() => setLang('en')}
          >
            {t.common.langEn}
          </button>
        </div>
        <div className="home-page__welcome-panel">
          <div>
            <p className="home-page__eyebrow">{t.home.dashboard}</p>
            <h1 className="home-page__greeting">
              {tx(t.home.greeting, { name: displayName || 'Guest' })}
            </h1>
            <p className="home-page__subtext">{t.home.subtext}</p>
          </div>
        </div>
        <section className="home-page__courses-section" aria-live="polite">
          <header className="home-page__courses-header">
            <h2 className="home-page__courses-title">{t.home.myCourses}</h2>
          </header>

          {isCoursesLoading ? (
            <p className="home-page__courses-state">{t.home.coursesLoading}</p>
          ) : null}

          {!isCoursesLoading && coursesError ? (
            <p className="home-page__courses-error" role="alert">
              {t.home.coursesError}
            </p>
          ) : null}

          {!isCoursesLoading && !coursesError ? (
            <ul className="home-page__courses-grid">
              {courses.map((course) => {
                const courseId = course.course_id ?? course.id ?? course.courseId ?? ''
                const courseName =
                  course.course_name ?? course.name ?? t.home.untitledCourse
                return (
                  <li key={String(courseId || courseName)} className="home-page__courses-grid-item">
                    <button
                      type="button"
                      className="home-page__course-card"
                      onClick={() => {
                        if (!courseId) return
                        navigate(`/course/${encodeURIComponent(String(courseId))}`, {
                          state: { courseName },
                        })
                      }}
                    >
                      <span className="home-page__course-card-icon-wrap" aria-hidden>
                        <IconFolder />
                      </span>
                      <span className="home-page__course-card-text">
                        <span className="home-page__course-name">{courseName}</span>
                      </span>
                      <IconChevronEnd />
                    </button>
                  </li>
                )
              })}
              <li className="home-page__courses-grid-item">
                <button
                  type="button"
                  className="home-page__course-card home-page__course-card--create"
                  onClick={() => setIsCreateCourseOpen(true)}
                >
                  <span className="home-page__course-card-icon-wrap home-page__course-card-icon-wrap--create" aria-hidden>
                    <IconPlus />
                  </span>
                  <span className="home-page__course-card-text">
                    <span className="home-page__course-name home-page__course-name--create">{t.home.createCourse}</span>
                  </span>
                </button>
              </li>
            </ul>
          ) : null}
        </section>
      </section>
      {isCreateCourseOpen ? (
        <div
          className="home-page__modal-backdrop"
          role="presentation"
          onClick={closeCreateCourseModal}
        >
          <section
            className="home-page__modal"
            role="dialog"
            aria-modal="true"
            aria-label={t.home.createCourseModalTitle}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="home-page__modal-title">{t.home.createCourseModalTitle}</h2>
            <p className="home-page__modal-subtitle">{t.home.createCourseModalSubtitle}</p>
            <form onSubmit={handleCreateCourseSubmit} className="home-page__modal-form">
              <label className="home-page__modal-label" htmlFor="course-name">
                {t.home.courseNameLabel}
              </label>
              <input
                id="course-name"
                className="home-page__modal-input"
                type="text"
                value={courseDraft.name}
                onChange={(e) => updateCourseDraft('name', e.target.value)}
                placeholder={t.home.courseNamePlaceholder}
              />

              <label className="home-page__modal-label" htmlFor="course-description">
                {t.home.courseDescriptionLabel}
              </label>
              <textarea
                id="course-description"
                className="home-page__modal-textarea"
                rows={4}
                value={courseDraft.description}
                onChange={(e) => updateCourseDraft('description', e.target.value)}
                placeholder={t.home.courseDescriptionPlaceholder}
              />

              <fieldset className="home-page__visibility-group">
                <legend className="home-page__modal-label">{t.home.visibilityLabel}</legend>
                <label className="home-page__radio-option">
                  <input
                    type="radio"
                    name="visibility"
                    value="private"
                    checked={courseDraft.visibility === 'private'}
                    onChange={(e) => updateCourseDraft('visibility', e.target.value)}
                  />
                  <span>{t.home.visibilityPrivate}</span>
                </label>
                <label className="home-page__radio-option">
                  <input
                    type="radio"
                    name="visibility"
                    value="public"
                    checked={courseDraft.visibility === 'public'}
                    onChange={(e) => updateCourseDraft('visibility', e.target.value)}
                  />
                  <span>{t.home.visibilityPublic}</span>
                </label>
              </fieldset>

              <div className="home-page__modal-actions">
                <button
                  type="button"
                  className="home-page__modal-cancel"
                  disabled={isCreatingCourse}
                  onClick={closeCreateCourseModal}
                >
                  {t.home.cancel}
                </button>
                <button type="submit" className="home-page__modal-submit" disabled={isCreatingCourse}>
                  {isCreatingCourse ? 'Creating...' : t.home.saveCourse}
                </button>
              </div>
              {createCourseError ? (
                <p className="home-page__modal-error" role="alert">
                  {createCourseError}
                </p>
              ) : null}
            </form>
          </section>
        </div>
      ) : null}
    </main>
  )
}
