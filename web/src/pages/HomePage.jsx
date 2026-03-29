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
        <p className="home-page__greeting home-page__greeting--muted">
          טוען…
        </p>
      </main>
    )
  }

  if (status === 'guest') {
    return <Navigate to="/" replace />
  }

  return (
    <main className="home-page" dir="rtl" lang="he">
      <p className="home-page__greeting">Hello, {displayName}</p>
      <button
        type="button"
        className="home-page__logout"
        onClick={handleLogout}
      >
        התנתקות
      </button>
    </main>
  )
}
