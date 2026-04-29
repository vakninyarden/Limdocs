import axios from 'axios'

const apiBaseUrl = import.meta.env.VITE_API_URL ?? ''

/**
 * @param {string} courseId
 * @param {string} idToken Cognito ID token (JWT)
 * @returns {Promise<Array<Record<string, unknown>>>}
 */
export async function getCourseDocuments(courseId, idToken) {
  if (!apiBaseUrl) {
    throw new Error('API is not configured. Set VITE_API_URL.')
  }
  if (!courseId) {
    throw new Error('Missing courseId.')
  }
  if (!idToken) {
    throw new Error('Missing idToken.')
  }

  const response = await axios.get(
    `${apiBaseUrl}/courses/${encodeURIComponent(courseId)}/documents`,
    {
      headers: {
        Authorization: `Bearer ${idToken}`,
      },
    },
  )

  const data = response?.data
  if (Array.isArray(data?.documents)) {
    return data.documents
  }
  return []
}

/**
 * @param {string} courseId
 * @param {string} documentId
 * @param {string} idToken Cognito ID token (JWT)
 * @returns {Promise<{ message?: string }>}
 */
export async function deleteDocument(courseId, documentId, idToken) {
  if (!apiBaseUrl) {
    throw new Error('API is not configured. Set VITE_API_URL.')
  }
  if (!courseId) {
    throw new Error('Missing courseId.')
  }
  if (!documentId) {
    throw new Error('Missing documentId.')
  }
  if (!idToken) {
    throw new Error('Missing idToken.')
  }

  const response = await axios.delete(
    `${apiBaseUrl}/courses/${encodeURIComponent(courseId)}/documents/${encodeURIComponent(documentId)}`,
    {
      headers: {
        Authorization: `Bearer ${idToken}`,
      },
    },
  )

  return response?.data ?? {}
}

/**
 * @param {string} courseId
 * @param {string} fileName
 * @param {string} fileType MIME type (must match S3 PUT Content-Type)
 * @param {string} idToken Cognito ID token (JWT)
 * @returns {Promise<{ upload_url: string, document_id: string, s3_key: string }>}
 */
export async function getUploadUrl(courseId, fileName, fileType, idToken) {
  if (!apiBaseUrl) {
    throw new Error('API is not configured. Set VITE_API_URL.')
  }
  if (!courseId) {
    throw new Error('Missing courseId.')
  }
  if (!idToken) {
    throw new Error('Missing idToken.')
  }

  const response = await axios.post(
    `${apiBaseUrl}/courses/${encodeURIComponent(courseId)}/upload-url`,
    { file_name: fileName, file_type: fileType },
    {
      headers: {
        Authorization: `Bearer ${idToken}`,
        'Content-Type': 'application/json',
      },
    },
  )

  return response.data
}

/**
 * @param {string} uploadUrl Pre-signed S3 PUT URL
 * @param {File|Blob} file
 * @param {string} fileType Same MIME type used when generating the URL
 */
export async function uploadFileToS3(uploadUrl, file, fileType) {
  await axios.put(uploadUrl, file, {
    headers: {
      'Content-Type': fileType,
    },
    maxBodyLength: Infinity,
    maxContentLength: Infinity,
  })
}

/**
 * @param {string} courseId
 * @param {string[]} documentIds
 * @param {string} idToken Cognito ID token (JWT)
 * @returns {Promise<Record<string, unknown>>}
 */
export async function generateQuiz(courseId, documentIds, idToken) {
  if (!apiBaseUrl) {
    throw new Error('API is not configured. Set VITE_API_URL.')
  }
  if (!courseId) {
    throw new Error('Missing courseId.')
  }
  if (!Array.isArray(documentIds) || documentIds.length === 0) {
    throw new Error('Missing documentIds.')
  }
  if (!idToken) {
    throw new Error('Missing idToken.')
  }

  const response = await axios.post(
    `${apiBaseUrl}/courses/${encodeURIComponent(courseId)}/generate-quiz`,
    { documentIds },
    {
      headers: {
        Authorization: `Bearer ${idToken}`,
        'Content-Type': 'application/json',
      },
    },
  )

  return response?.data ?? {}
}
