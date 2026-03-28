export const routes = {
  dashboard: '/',
  assets: '/assets',
  scans: '/scans',
  scanTool: '/scans/:toolId',
  findings: '/findings',
  attackSurface: '/attack-surface',
  reports: '/reports',
  settings: '/settings',
  history: '/history',
  task: '/task/:taskId',
} as const

export const routePath = {
  scanTool: (toolId: string) => `${routes.scans}/${encodeURIComponent(toolId)}`,
  task: (taskId: string) => `/task/${encodeURIComponent(taskId)}`,
} as const

