export const routes = {
  dashboard: '/',
  assets: '/assets',
  toolkit: '/toolkit',
  scanTool: '/toolkit/:toolId',
  findings: '/findings',
  scans: '/scans',
  reports: '/reports',
  settings: '/settings',
  task: '/task/:taskId',
} as const

export const routePath = {
  scanTool: (toolId: string) => `${routes.toolkit}/${encodeURIComponent(toolId)}`,
  task: (taskId: string) => `/task/${encodeURIComponent(taskId)}`,
} as const

