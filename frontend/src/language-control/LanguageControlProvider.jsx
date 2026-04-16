import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { languageContent } from './languageContent.js'

const LanguageControlContext = createContext(null)

const STORAGE_KEY = 'limdocs.lang'
const DEFAULT_LANG = 'he'

function formatMessage(template, vars = {}) {
  return String(template).replace(/\{(\w+)\}/g, (_, key) => vars[key] ?? '')
}

export function LanguageControlProvider({ children }) {
  const [lang, setLang] = useState(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    return stored === 'en' || stored === 'he' ? stored : DEFAULT_LANG
  })

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, lang)
  }, [lang])

  const value = useMemo(() => {
    const t = languageContent[lang] ?? languageContent[DEFAULT_LANG]
    return {
      lang,
      setLang,
      dir: lang === 'he' ? 'rtl' : 'ltr',
      t,
      tx: (template, vars) => formatMessage(template, vars),
    }
  }, [lang])

  return (
    <LanguageControlContext.Provider value={value}>
      {children}
    </LanguageControlContext.Provider>
  )
}

export function useLanguageControl() {
  const context = useContext(LanguageControlContext)
  if (!context) {
    throw new Error(
      'useLanguageControl must be used within LanguageControlProvider',
    )
  }
  return context
}
