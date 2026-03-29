import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './LoginPage.css'

const initialLogin = { identifier: '', password: '' }
const initialSignup = {
  firstName: '',
  lastName: '',
  email: '',
  username: '',
  password: '',
}

function Feedback({ feedback }) {
  if (!feedback) return null
  const className =
    feedback.kind === 'success'
      ? 'login-page__feedback login-page__feedback--success'
      : 'login-page__feedback login-page__feedback--error'
  return (
    <p className={className} role="alert">
      {feedback.he}
    </p>
  )
}

export default function LoginPage() {
  const navigate = useNavigate()
  const [mode, setMode] = useState('login')
  const [login, setLogin] = useState(initialLogin)
  const [signup, setSignup] = useState(initialSignup)
  const [fieldErrors, setFieldErrors] = useState({})
  const [feedback, setFeedback] = useState(null)

  const goLogin = () => {
    setFeedback(null)
    setMode('login')
  }

  const goSignup = () => {
    setFeedback(null)
    setFieldErrors({})
    setMode('signup')
  }

  const updateLogin = (field, value) => {
    setLogin((prev) => ({ ...prev, [field]: value }))
  }

  const updateSignup = (field, value) => {
    setSignup((prev) => ({ ...prev, [field]: value }))
    setFieldErrors((prev) => {
      if (!prev[field]) return prev
      const next = { ...prev }
      delete next[field]
      return next
    })
  }

  const handleLoginSubmit = (e) => {
    e.preventDefault()
    setFeedback(null)
    const username = login.identifier.trim()
    if (!username || !login.password) {
      setFeedback({
        kind: 'error',
        he: 'נא למלא שם משתמש/אימייל וסיסמה.',
      })
      return
    }
    navigate('/home', { replace: true, state: { username } })
  }

  const handleSignupSubmit = (e) => {
    e.preventDefault()
    setFeedback(null)
    setFieldErrors({})
    const username = signup.username.trim()
    const email = signup.email.trim()
    const firstName = signup.firstName.trim()
    const lastName = signup.lastName.trim()
    const password = signup.password

    const nextFieldErrors = {}
    if (!firstName) nextFieldErrors.firstName = 'נא להזין שם פרטי'
    if (!lastName) nextFieldErrors.lastName = 'נא להזין שם משפחה'
    if (!email) nextFieldErrors.email = 'נא להזין כתובת אימייל'
    if (!username) nextFieldErrors.username = 'נא להזין שם משתמש'
    if (!password) nextFieldErrors.password = 'נא להזין סיסמה'
    if (password && password.length < 8) {
      nextFieldErrors.password = 'הסיסמה חייבת להכיל לפחות 8 תווים'
    }
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      nextFieldErrors.email = 'כתובת אימייל לא תקינה'
    }

    if (Object.keys(nextFieldErrors).length > 0) {
      setFieldErrors(nextFieldErrors)
      setFeedback({ kind: 'error', he: 'יש לתקן את השדות המסומנים באדום.' })
      return
    }

    navigate('/home', { replace: true, state: { username } })
  }

  const handleForgotPassword = () => {
    console.log('[שכחתי סיסמה]', { identifier: login.identifier })
  }

  return (
    <div className="login-page" dir="rtl" lang="he">
      <div className="login-page__inner">
        <header className="login-page__brand">
          <div className="login-page__logo" aria-hidden>
            L
          </div>
          <h1 className="login-page__title">לימדוקס</h1>
          <p className="login-page__subtitle">
            למידה מותאמת אישית — התחברו או צרו חשבון
          </p>
        </header>

        <div className="login-page__card">
          <Feedback feedback={feedback} />

          {mode === 'login' ? (
            <form
              aria-label="טופס התחברות"
              onSubmit={handleLoginSubmit}
              noValidate
            >
              <div className="login-page__field">
                <label className="login-page__label" htmlFor="login-identifier">
                  שם משתמש או אימייל
                </label>
                <input
                  id="login-identifier"
                  className="login-page__input"
                  type="text"
                  name="identifier"
                  autoComplete="username"
                  value={login.identifier}
                  onChange={(e) =>
                    updateLogin('identifier', e.target.value)
                  }
                />
              </div>
              <div className="login-page__field">
                <label className="login-page__label" htmlFor="login-password">
                  סיסמה
                </label>
                <input
                  id="login-password"
                  className="login-page__input"
                  type="password"
                  name="password"
                  autoComplete="current-password"
                  value={login.password}
                  onChange={(e) => updateLogin('password', e.target.value)}
                />
              </div>
              <button type="submit" className="login-page__submit">
                התחברות
              </button>
              <div className="login-page__links">
                <button
                  type="button"
                  className="login-page__link"
                  onClick={handleForgotPassword}
                >
                  שכחתי סיסמה
                </button>
                <button
                  type="button"
                  className="login-page__link"
                  onClick={goSignup}
                >
                  צור חשבון חדש
                </button>
              </div>
            </form>
          ) : (
            <form
              aria-label="טופס יצירת חשבון"
              onSubmit={handleSignupSubmit}
              noValidate
            >
              <div className="login-page__field">
                <label className="login-page__label" htmlFor="signup-first-name">
                  שם פרטי
                </label>
                <input
                  id="signup-first-name"
                  className={`login-page__input ${fieldErrors.firstName ? 'login-page__input--error' : ''}`}
                  type="text"
                  name="firstName"
                  autoComplete="given-name"
                  value={signup.firstName}
                  onChange={(e) => updateSignup('firstName', e.target.value)}
                />
                {fieldErrors.firstName ? (
                  <span className="field-error">{fieldErrors.firstName}</span>
                ) : null}
              </div>
              <div className="login-page__field">
                <label className="login-page__label" htmlFor="signup-last-name">
                  שם משפחה
                </label>
                <input
                  id="signup-last-name"
                  className={`login-page__input ${fieldErrors.lastName ? 'login-page__input--error' : ''}`}
                  type="text"
                  name="lastName"
                  autoComplete="family-name"
                  value={signup.lastName}
                  onChange={(e) => updateSignup('lastName', e.target.value)}
                />
                {fieldErrors.lastName ? (
                  <span className="field-error">{fieldErrors.lastName}</span>
                ) : null}
              </div>
              <div className="login-page__field">
                <label className="login-page__label" htmlFor="signup-email">
                  אימייל
                </label>
                <input
                  id="signup-email"
                  className={`login-page__input ${fieldErrors.email ? 'login-page__input--error' : ''}`}
                  type="email"
                  name="email"
                  autoComplete="email"
                  value={signup.email}
                  onChange={(e) => updateSignup('email', e.target.value)}
                />
                {fieldErrors.email ? (
                  <span className="field-error">{fieldErrors.email}</span>
                ) : null}
              </div>
              <div className="login-page__field">
                <label className="login-page__label" htmlFor="signup-username">
                  שם משתמש
                </label>
                <input
                  id="signup-username"
                  className={`login-page__input ${fieldErrors.username ? 'login-page__input--error' : ''}`}
                  type="text"
                  name="username"
                  autoComplete="username"
                  value={signup.username}
                  onChange={(e) => updateSignup('username', e.target.value)}
                />
                {fieldErrors.username ? (
                  <span className="field-error">{fieldErrors.username}</span>
                ) : null}
              </div>
              <div className="login-page__field">
                <label className="login-page__label" htmlFor="signup-password">
                  סיסמה
                </label>
                <input
                  id="signup-password"
                  className={`login-page__input ${fieldErrors.password ? 'login-page__input--error' : ''}`}
                  type="password"
                  name="password"
                  autoComplete="new-password"
                  value={signup.password}
                  onChange={(e) => updateSignup('password', e.target.value)}
                />
                {fieldErrors.password ? (
                  <span className="field-error">{fieldErrors.password}</span>
                ) : null}
              </div>
              <button type="submit" className="login-page__submit">
                צור חשבון
              </button>
              <div className="login-page__links">
                <button
                  type="button"
                  className="login-page__link"
                  onClick={goLogin}
                >
                  כבר יש לך חשבון? התחבר
                </button>
              </div>
            </form>
          )}
        </div>

        <p className="login-page__footer">לימדוקס — פלטפורמת למידה אדפטיבית</p>
      </div>
    </div>
  )
}
