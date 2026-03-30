import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { confirmSignUp, getCurrentUser, signIn, signUp } from 'aws-amplify/auth'
import './LoginPage.css'

function logAuthError(context, error) {
  const message = error?.message ?? String(error)
  const name = error?.name ?? error?.code
  console.warn('[Auth i18n draft]', context, { name, message, error })
}

const initialLogin = { identifier: '', password: '' }
const initialSignup = {
  firstName: '',
  lastName: '',
  email: '',
  username: '',
  password: '',
}

const signupRequirementMessages = {
  fullName: 'חובה להזין שם מלא (לפחות 2 מילים).',
  email: 'יש להזין כתובת אימייל תקינה (למשל: name@example.com).',
  username: 'שם משתמש חייב להכיל לפחות 3 תווים, ללא רווחים.',
  password:
    'הסיסמה אינה עומדת בדרישות. עליה להכיל:\n • לפחות 8 תווים\n • אות גדולה (A-Z) ואות קטנה (a-z)\n • לפחות מספר אחד (0-9)\n • תו מיוחד (למשל: !, @, #, $)',
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
  const [loginErrors, setLoginErrors] = useState({})
  const [signup, setSignup] = useState(initialSignup)
  const [fieldErrors, setFieldErrors] = useState({})
  const [confirmCode, setConfirmCode] = useState('')
  const [pendingUsername, setPendingUsername] = useState('')
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState(null)

  useEffect(() => {
    if (mode !== 'login' && mode !== 'signup') return
    let cancelled = false
    ;(async () => {
      try {
        await getCurrentUser()
        if (!cancelled) navigate('/home', { replace: true })
      } catch {
        /* no session */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [mode, navigate])

  const goLogin = () => {
    setFeedback(null)
    setLoginErrors({})
    setMode('login')
  }

  const goSignup = () => {
    setFeedback(null)
    setLoginErrors({})
    setFieldErrors({})
    setMode('signup')
  }

  const updateLogin = (field, value) => {
    setLogin((prev) => ({ ...prev, [field]: value }))
    setLoginErrors((prev) => {
      if (!prev[field]) return prev
      const next = { ...prev }
      delete next[field]
      return next
    })
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

  const handleLoginSubmit = async (e) => {
    e.preventDefault()
    setFeedback(null)
    setLoginErrors({})
    const username = login.identifier.trim()
    const nextLoginErrors = {}
    if (!username) {
      nextLoginErrors.identifier = 'יש להזין שם משתמש או אימייל.'
    }
    if (!login.password) {
      nextLoginErrors.password = 'יש להזין סיסמה.'
    }
    if (Object.keys(nextLoginErrors).length > 0) {
      setLoginErrors(nextLoginErrors)
      setFeedback({
        kind: 'error',
        he: 'יש למלא את השדות המסומנים באדום.',
      })
      return
    }
    setBusy(true)
    try {
      const out = await signIn({ username, password: login.password })
      const signInDone =
        out.isSignedIn || out.nextStep?.signInStep === 'DONE'
      if (signInDone) {
        navigate('/home', { replace: true })
        return
      }
      logAuthError('signIn nextStep', out.nextStep)
      setFeedback({
        kind: 'error',
        he: 'לא ניתן להשלים כניסה. ייתכן שנדרש שלב נוסף (למשל אימות דו-שלבי).',
      })
    } catch (err) {
      if (err?.name === 'UserAlreadyAuthenticatedException') {
        navigate('/home', { replace: true })
        return
      }
      logAuthError('signIn', err)
      const errorName = err?.name ?? err?.code
      if (errorName === 'UserNotFoundException') {
        setLoginErrors({
          identifier: 'שם המשתמש או האימייל אינם קיימים במערכת',
        })
      } else if (errorName === 'NotAuthorizedException') {
        setLoginErrors({
          password: 'הסיסמה שהזנת אינה נכונה. נסה שנית.',
        })
      } else if (errorName === 'UserNotConfirmedException') {
        setLoginErrors({
          identifier: 'חשבונך טרם אומת. בדוק את המייל לקוד אישור.',
        })
      } else {
        setFeedback({
          kind: 'error',
          he: 'התחברות נכשלה. בדקו את הפרטים או נסו שוב מאוחר יותר.',
        })
      }
    } finally {
      setBusy(false)
    }
  }

  const handleSignupSubmit = async (e) => {
    e.preventDefault()
    setFeedback(null)
    setFieldErrors({})
    const username = signup.username.trim()
    const email = signup.email.trim()
    const firstName = signup.firstName.trim()
    const lastName = signup.lastName.trim()
    const password = signup.password

    const nextFieldErrors = {}
    const fullName = `${firstName} ${lastName}`.trim()
    const fullNameWords = fullName.split(/\s+/).filter(Boolean)
    const hasValidFullName = fullNameWords.length >= 2
    const hasValidEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
    const hasValidUsername = username.length >= 3 && !/\s/.test(username)
    const hasValidPassword =
      password.length >= 8 &&
      /[A-Z]/.test(password) &&
      /[a-z]/.test(password) &&
      /\d/.test(password) &&
      /[^A-Za-z0-9]/.test(password)

    if (!hasValidFullName) {
      nextFieldErrors.firstName = signupRequirementMessages.fullName
      nextFieldErrors.lastName = signupRequirementMessages.fullName
    }
    if (!hasValidEmail) {
      nextFieldErrors.email = signupRequirementMessages.email
    }
    if (!hasValidUsername) {
      nextFieldErrors.username = signupRequirementMessages.username
    }
    if (!hasValidPassword) {
      nextFieldErrors.password = signupRequirementMessages.password
    }

    if (Object.keys(nextFieldErrors).length > 0) {
      setFieldErrors(nextFieldErrors)
      setFeedback({ kind: 'error', he: 'יש לתקן את השדות המסומנים באדום.' })
      return
    }
    setBusy(true)
    // #region agent log
    fetch('http://127.0.0.1:7342/ingest/c12bd9e5-3c3e-438c-8677-68452c921326',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'4bfbe0'},body:JSON.stringify({sessionId:'4bfbe0',runId:'signup-debug-1',hypothesisId:'H2',location:'src/pages/LoginPage.jsx:104',message:'signUp submit payload summary',data:{usernameLength:username.length,emailDomain:(email.split('@')[1]||'').toLowerCase(),firstNameLength:firstName.length,lastNameLength:lastName.length,passwordLength:password.length,isOnline:navigator.onLine},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    try {
      const out = await signUp({
        username,
        password,
        options: {
          userAttributes: {
            email,
            given_name: firstName,
            family_name: lastName,
          },
        },
      })
      const step = out.nextStep?.signUpStep
      // #region agent log
      fetch('http://127.0.0.1:7342/ingest/c12bd9e5-3c3e-438c-8677-68452c921326',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'4bfbe0'},body:JSON.stringify({sessionId:'4bfbe0',runId:'signup-debug-1',hypothesisId:'H3',location:'src/pages/LoginPage.jsx:117',message:'signUp response received',data:{isSignUpComplete:Boolean(out.isSignUpComplete),signUpStep:step||'none',codeDeliveryMedium:out.nextStep?.codeDeliveryDetails?.deliveryMedium||'none'},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      if (step === 'CONFIRM_SIGN_UP') {
        setPendingUsername(username)
        setConfirmCode('')
        setMode('confirm')
        setFeedback({
          kind: 'success',
          he: 'נשלח קוד אימות לאימייל. הזינו אותו למטה לאישור החשבון.',
        })
        return
      }
      if (out.isSignUpComplete) {
        setFeedback({
          kind: 'success',
          he: 'ההרשמה הושלמה. כעת ניתן להתחבר.',
        })
        setMode('login')
        return
      }
      logAuthError('signUp unexpected nextStep', out)
      setFeedback({
        kind: 'error',
        he: 'ההרשמה לא הושלמה. נסו שוב או פנו לתמיכה.',
      })
    } catch (err) {
      logAuthError('signUp', err)
      // #region agent log
      fetch('http://127.0.0.1:7342/ingest/c12bd9e5-3c3e-438c-8677-68452c921326',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'4bfbe0'},body:JSON.stringify({sessionId:'4bfbe0',runId:'signup-debug-1',hypothesisId:'H4',location:'src/pages/LoginPage.jsx:145',message:'signUp error caught',data:{errorName:err?.name||'unknown',errorCode:err?.code||'unknown',message:String(err?.message||'').slice(0,240),suggestion:err?.recoverySuggestion||''},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      const errorName = err?.name ?? err?.code
      if (errorName === 'UsernameExistsException') {
        setFieldErrors({ username: signupRequirementMessages.username })
      } else if (errorName === 'InvalidParameterException') {
        setFieldErrors({ email: signupRequirementMessages.email })
      } else if (errorName === 'InvalidPasswordException') {
        setFieldErrors({
          password: signupRequirementMessages.password,
        })
      }
      setFeedback({ kind: 'error', he: 'הרשמה נכשלה. בדקו את השדות ונסו שוב.' })
    } finally {
      setBusy(false)
    }
  }

  const handleConfirmSubmit = async (e) => {
    e.preventDefault()
    setFeedback(null)
    const code = confirmCode.trim()
    if (!pendingUsername || !code) {
      setFeedback({ kind: 'error', he: 'נא להזין את קוד האימות מהאימייל.' })
      return
    }
    setBusy(true)
    try {
      await confirmSignUp({
        username: pendingUsername,
        confirmationCode: code,
      })
      setConfirmCode('')
      setPendingUsername('')
      setFeedback({
        kind: 'success',
        he: 'החשבון אושר. ניתן להתחבר.',
      })
      setMode('login')
    } catch (err) {
      logAuthError('confirmSignUp', err)
      setFeedback({
        kind: 'error',
        he: 'אימות נכשל. בדקו את הקוד או שלחו קוד חדש מקונסולת Cognito.',
      })
    } finally {
      setBusy(false)
    }
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
                  className={`login-page__input ${loginErrors.identifier ? 'login-page__input--error' : ''}`}
                  type="text"
                  name="identifier"
                  autoComplete="username"
                  value={login.identifier}
                  onChange={(e) =>
                    updateLogin('identifier', e.target.value)
                  }
                />
                {loginErrors.identifier ? (
                  <span className="field-error">{loginErrors.identifier}</span>
                ) : null}
                {loginErrors.identifier === 'חשבונך טרם אומת. בדוק את המייל לקוד אישור.' ? (
                  <button
                    type="button"
                    className="login-page__link"
                    onClick={() => {
                      setPendingUsername(login.identifier.trim())
                      setMode('confirm')
                    }}
                  >
                    מעבר למסך אישור חשבון
                  </button>
                ) : null}
              </div>
              <div className="login-page__field">
                <label className="login-page__label" htmlFor="login-password">
                  סיסמה
                </label>
                <input
                  id="login-password"
                  className={`login-page__input ${loginErrors.password ? 'login-page__input--error' : ''}`}
                  type="password"
                  name="password"
                  autoComplete="current-password"
                  value={login.password}
                  onChange={(e) => updateLogin('password', e.target.value)}
                />
                {loginErrors.password ? (
                  <span className="field-error">{loginErrors.password}</span>
                ) : null}
              </div>
              <button
                type="submit"
                className="login-page__submit"
                disabled={busy}
              >
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
          ) : mode === 'signup' ? (
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
              <button
                type="submit"
                className="login-page__submit"
                disabled={busy}
              >
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
          ) : (
            <form
              aria-label="אישור חשבון"
              onSubmit={handleConfirmSubmit}
              noValidate
            >
              <p className="login-page__label" style={{ marginBottom: '0.75rem' }}>
                הזינו את קוד האימות שנשלח ל־
                <strong dir="ltr"> {signup.email.trim() || 'האימייל שלך'}</strong>
              </p>
              <div className="login-page__field">
                <label className="login-page__label" htmlFor="confirm-code">
                  קוד אימות
                </label>
                <input
                  id="confirm-code"
                  className="login-page__input"
                  type="text"
                  name="confirmationCode"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={confirmCode}
                  onChange={(e) => setConfirmCode(e.target.value)}
                />
              </div>
              <button
                type="submit"
                className="login-page__submit"
                disabled={busy}
              >
                אשר חשבון
              </button>
              <div className="login-page__links">
                <button
                  type="button"
                  className="login-page__link"
                  onClick={() => {
                    setPendingUsername('')
                    setConfirmCode('')
                    goLogin()
                  }}
                >
                  חזרה להתחברות
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
