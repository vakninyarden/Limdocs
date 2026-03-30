import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import {
  fetchUserAttributes,
  getCurrentUser,
  signOut,
} from 'aws-amplify/auth'
import './HomePage.css'

function logAuthError(context, error) {
  const message = error?.message ?? String(error)
  const name = error?.name ?? error?.code
  console.warn('[Auth i18n draft]', context, { name, message, error })
}

export default function HomePage() {
  const navigate = useNavigate()
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
      <main className="home-page" dir="rtl" lang="he">
        <section className="home-page__loading">
          <p className="home-page__greeting home-page__greeting--muted">טוען…</p>
        </section>
      </main>
    )
  }

  if (status === 'guest') {
    return <Navigate to="/" replace />
  }

  return (
    <main className="home-page" dir="rtl" lang="he">
      <aside className="home-page__sidebar" aria-label="ניווט ראשי">
        <div className="home-page__brand">
          <div className="home-page__logo" aria-hidden>
            L
          </div>
          <p className="home-page__brand-name">Limdocs</p>
        </div>

        <nav className="home-page__menu">
          <button type="button" className="home-page__menu-item home-page__menu-item--active">
            <span aria-hidden>🏠</span>
            <span>דאשבורד</span>
          </button>
          <button type="button" className="home-page__menu-item">
            <span aria-hidden>📚</span>
            <span>הקורסים שלי</span>
          </button>
          <button type="button" className="home-page__menu-item">
            <span aria-hidden>👤</span>
            <span>פרופיל</span>
          </button>
        </nav>

        <button type="button" className="home-page__logout" onClick={handleLogout}>
          <span aria-hidden>↩</span>
          <span>התנתקות</span>
        </button>
      </aside>

      <section className="home-page__content">
        <div className="home-page__welcome-panel">
          <div>
            <p className="home-page__eyebrow">דאשבורד</p>
            <h1 className="home-page__greeting">שלום, {displayName || 'Guest'}</h1>
            <p className="home-page__subtext">מוכנים להתחיל? כאן תוכלו להתחיל לבנות סביבת למידה חדשה.</p>
          </div>
          <button type="button" className="home-page__primary-action">
            ליצירת קורס חדש
          </button>
        </div>
      </section>
    </main>
  )
}
