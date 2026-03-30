import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './auth-config.js'
import './index.css'
import App from './App.jsx'
import { LanguageControlProvider } from './language-control/LanguageControlProvider.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <LanguageControlProvider>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </LanguageControlProvider>
  </StrictMode>,
)
