import { useEffect, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { getCurrentUser } from 'aws-amplify/auth'
import './CoursePage.css'
import { useLanguageControl } from '../language-control/LanguageControlProvider.jsx'

const MOCK_MATERIALS_COUNT = 1

export default function CoursePage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { t, lang, setLang, dir, tx } = useLanguageControl()
  const [authStatus, setAuthStatus] = useState('loading')

  const courseNameFromState =
    typeof location.state?.courseName === 'string' ? location.state.courseName.trim() : ''

  const displayCourseName = courseNameFromState || t.home.untitledCourse

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
        <button type="button" className="course-page__upload-btn">
          {t.coursePage.uploadMaterial}
        </button>
      </div>

      <section className="course-page__materials-section" aria-label={t.coursePage.materialsSectionLabel}>
        <h2 className="course-page__materials-heading">{t.coursePage.materialsHeading}</h2>
        <p className="course-page__materials-empty">{t.coursePage.materialsEmpty}</p>
      </section>
    </main>
  )
}
