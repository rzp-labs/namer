/**
 * Gets the CSRF token from the meta tag in the document head.
 *
 * @returns {string|null} The CSRF token, or null if not found.
 */
export function getToken () {
  const meta = document.querySelector('meta[name="csrf-token"]')
  return meta ? meta.getAttribute('content') : null
}

/**
 * Updates the CSRF token in the meta tag in the document head.
 * If the meta tag doesn't exist, it will be created.
 *
 * @param {string} token - The new CSRF token.
 */
export function updateToken (token) {
  if (!token) {
    return
  }

  let meta = document.querySelector('meta[name="csrf-token"]')
  if (!meta) {
    meta = document.createElement('meta')
    meta.setAttribute('name', 'csrf-token')
    document.head.appendChild(meta)
  }

  meta.setAttribute('content', token)
}