export function normalizeCourseVisibility(value) {
  return value === 'PUBLIC' ? 'PUBLIC' : 'PRIVATE'
}
