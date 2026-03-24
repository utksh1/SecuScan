const API_BASE = '/api/v1'

class APIError extends Error {
  constructor(message, status, data) {
    super(message)
    this.status = status
    this.data = data
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    const data = await response.json()

    if (!response.ok) {
      throw new APIError(
        data.detail || 'Request failed',
        response.status,
        data
      )
    }

    return data
  } catch (error) {
    if (error instanceof APIError) throw error
    throw new APIError('Network error', 0, { message: error.message })
  }
}

export const api = {
  // Health check
  health: () => request('/health'),

  // Plugins
  getPlugins: () => request('/plugins'),
  getPluginSchema: (pluginId) => request(`/plugin/${pluginId}/schema`),
  getPresets: () => request('/presets'),

  // Tasks
  startTask: (data) => request('/task/start', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  
  getTaskStatus: (taskId) => request(`/task/${taskId}/status`),
  getTaskResult: (taskId) => request(`/task/${taskId}/result`),
  cancelTask: (taskId) => request(`/task/${taskId}/cancel`, { method: 'POST' }),
  deleteTask: (taskId) => request(`/task/${taskId}`, { method: 'DELETE' }),
  
  getTasks: (params = {}) => {
    const query = new URLSearchParams(params).toString()
    return request(`/tasks${query ? `?${query}` : ''}`)
  },

  // Settings
  getSettings: () => request('/settings'),
}
