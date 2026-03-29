import { useState } from 'react'
import './LoginPage.css'

const initialLogin = { identifier: '', password: '' }
const initialSignup = { fullName: '', email: '', username: '', password: '' }

export default function LoginPage() {
  const [mode, setMode] = useState('login')
  const [login, setLogin] = useState(initialLogin)
  const [signup, setSignup] = useState(initialSignup)

  const updateLogin = (field, value) => {
    setLogin((prev) => ({ ...prev, [field]: value }))
  }

  const updateSignup = (field, value) => {
    setSignup((prev) => ({ ...prev, [field]: value }))
  }

  const handleLoginSubmit = (e) => {
    e.preventDefault()
    console.log('[התחברות]', login)
  }

  const handleSignupSubmit = (e) => {
    e.preventDefault()
    console.log('[הרשמה]', signup)
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
                  onClick={() => setMode('signup')}
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
                <label className="login-page__label" htmlFor="signup-name">
                  שם מלא
                </label>
                <input
                  id="signup-name"
                  className="login-page__input"
                  type="text"
                  name="fullName"
                  autoComplete="name"
                  value={signup.fullName}
                  onChange={(e) => updateSignup('fullName', e.target.value)}
                />
              </div>
              <div className="login-page__field">
                <label className="login-page__label" htmlFor="signup-email">
                  אימייל
                </label>
                <input
                  id="signup-email"
                  className="login-page__input"
                  type="email"
                  name="email"
                  autoComplete="email"
                  value={signup.email}
                  onChange={(e) => updateSignup('email', e.target.value)}
                />
              </div>
              <div className="login-page__field">
                <label className="login-page__label" htmlFor="signup-username">
                  שם משתמש
                </label>
                <input
                  id="signup-username"
                  className="login-page__input"
                  type="text"
                  name="username"
                  autoComplete="username"
                  value={signup.username}
                  onChange={(e) => updateSignup('username', e.target.value)}
                />
              </div>
              <div className="login-page__field">
                <label className="login-page__label" htmlFor="signup-password">
                  סיסמה
                </label>
                <input
                  id="signup-password"
                  className="login-page__input"
                  type="password"
                  name="password"
                  autoComplete="new-password"
                  value={signup.password}
                  onChange={(e) => updateSignup('password', e.target.value)}
                />
              </div>
              <button type="submit" className="login-page__submit">
                צור חשבון
              </button>
              <div className="login-page__links">
                <button
                  type="button"
                  className="login-page__link"
                  onClick={() => setMode('login')}
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
