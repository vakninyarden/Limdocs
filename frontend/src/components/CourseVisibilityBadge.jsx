import { normalizeCourseVisibility } from '../utils/courseVisibility.js'
import './CourseVisibilityBadge.css'

function GlobeIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M3.5 12h17M12 3c2.6 2.4 3.9 5.6 3.9 9s-1.3 6.6-3.9 9c-2.6-2.4-3.9-5.6-3.9-9s1.3-6.6 3.9-9Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function LockIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="5" y="11" width="14" height="10" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M8 11V8a4 4 0 0 1 8 0v3"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  )
}

export default function CourseVisibilityBadge({ visibility, labels }) {
  const isPublic = normalizeCourseVisibility(visibility) === 'PUBLIC'
  const className = isPublic
    ? 'course-visibility-badge course-visibility-badge--public'
    : 'course-visibility-badge course-visibility-badge--private'

  return (
    <span className={className}>
      {isPublic ? <GlobeIcon /> : <LockIcon />}
      <span>{isPublic ? labels.visibilityPublic : labels.visibilityPrivate}</span>
    </span>
  )
}
