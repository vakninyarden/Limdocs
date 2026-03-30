import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import {
  fetchUserAttributes,
  getCurrentUser,
  signOut,
} from 'aws-amplify/auth'
import './HomePage.css'
import { useLanguageControl } from '../language-control/LanguageControlProvider.jsx'

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
          attrs.name ??
          attrs.preferred_username ??
          attrs.email ??
          user.username
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

  const handleLogout = async () => {
    try {
      await signOut()
    } catch (e) {
      logAuthError('signOut', e)
    }
    navigate('/', { replace: true })
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
            <span aria-hidden>🏠</span>
            <span>{t.home.dashboard}</span>
          </button>
          <button type="button" className="home-page__menu-item">
            <span aria-hidden>📚</span>
            <span>{t.home.myCourses}</span>
          </button>
          <button type="button" className="home-page__menu-item">
            <span aria-hidden>👤</span>
            <span>{t.home.profile}</span>
          </button>
        </nav>

        <button type="button" className="home-page__logout" onClick={handleLogout}>
          <span aria-hidden>↩</span>
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
          <button type="button" className="home-page__primary-action">
            {t.home.createCourse}
          </button>
        </div>
      </section>
    </main>
  )
}
