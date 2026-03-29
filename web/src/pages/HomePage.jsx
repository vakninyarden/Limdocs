import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import './HomePage.css'

export default function HomePage() {
  const location = useLocation()
  const navigate = useNavigate()
  const username = location.state?.username

  if (typeof username !== 'string' || username.trim() === '') {
    return <Navigate to="/" replace />
  }

  const handleLogout = () => {
    navigate('/', { replace: true })
  }

  return (
    <main className="home-page" dir="rtl" lang="he">
      <p className="home-page__greeting">Hello, {username.trim()}</p>
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
