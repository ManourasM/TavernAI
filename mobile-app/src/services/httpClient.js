/**
 * HTTP Client Wrapper
 * 
 * Provides a fetch wrapper that automatically includes Authorization header for authenticated requests.
 * Replaces need to manually add headers in every service.
 */

import { getAuthHeader } from './authService';

/**
 * HTTP client with automatic auth header injection
 * 
 * This wrapper enhances fetch with:
 * - Automatic Authorization: Bearer <token> header injection
 * - Consistent error handling
 * - Debug logging
 * 
 * @param {string} url - URL to fetch
 * @param {Object} options - Fetch options (method, headers, body, etc)
 * @returns {Promise<Response>} Fetch response
 * 
 * @example
 * // Simple GET
 * const result = await httpClient('/api/menu');
 * 
 * // With options
 * const result = await httpClient('/api/menu', {
 *   method: 'POST',
 *   body: JSON.stringify({ data: '...' })
 * });
 */
export async function httpClient(url, options = {}) {
  try {
    // Prepare headers
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };
    
    // Add auth header if token exists
    const authHeader = getAuthHeader();
    if (authHeader) {
      Object.assign(headers, authHeader);
    }
    
    // Make request
    const response = await fetch(url, {
      ...options,
      headers,
      cache: options.cache !== undefined ? options.cache : 'no-store'
    });
    
    // Log for debugging
    if (!response.ok) {
      console.warn(`[httpClient] ${options.method || 'GET'} ${url}: ${response.status}`);
    }
    
    return response;
  } catch (error) {
    console.error('[httpClient] Request failed:', error);
    throw error;
  }
}

/**
 * Typed HTTP GET
 * @param {string} url - URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise<Object>} Parsed JSON response
 */
export async function httpGet(url, options = {}) {
  const response = await httpClient(url, { ...options, method: 'GET' });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Typed HTTP POST
 * @param {string} url - URL to fetch
 * @param {Object} data - Data to POST
 * @param {Object} options - Additional fetch options
 * @returns {Promise<Object>} Parsed JSON response
 */
export async function httpPost(url, data, options = {}) {
  const response = await httpClient(url, {
    ...options,
    method: 'POST',
    body: JSON.stringify(data)
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Typed HTTP PUT
 * @param {string} url - URL to fetch
 * @param {Object} data - Data to PUT
 * @param {Object} options - Additional fetch options
 * @returns {Promise<Object>} Parsed JSON response
 */
export async function httpPut(url, data, options = {}) {
  const response = await httpClient(url, {
    ...options,
    method: 'PUT',
    body: JSON.stringify(data)
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Typed HTTP DELETE
 * @param {string} url - URL to fetch
 * @param {Object} options - Additional fetch options
 * @returns {Promise<Object>} Parsed JSON response or null
 */
export async function httpDelete(url, options = {}) {
  const response = await httpClient(url, {
    ...options,
    method: 'DELETE'
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  
  // DELETE might return empty response
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

export default {
  httpClient,
  httpGet,
  httpPost,
  httpPut,
  httpDelete
};
