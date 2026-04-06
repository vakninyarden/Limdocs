import axios from 'axios'

const apiBaseUrl = import.meta.env.VITE_API_URL ?? ''

export async function getUserCourses(userId, idToken) {
  if (!apiBaseUrl) {
    throw new Error('API is not configured. Set VITE_API_URL.')
  }
  if (!userId) {
    throw new Error('Missing userId.')
  }
  if (!idToken) {
    throw new Error('Missing idToken.')
  }

  const response = await axios.get(`${apiBaseUrl}/users/${encodeURIComponent(userId)}/courses`, {
    headers: {
      Authorization: `Bearer ${idToken}`,
    },
  })

  const payload = response?.data
  if (Array.isArray(payload)) {
    return payload
  }
  if (Array.isArray(payload?.courses)) {
    return payload.courses
  }
  return []
}
