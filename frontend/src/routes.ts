export const routes = {
  dashboard: '/',
  toolkit: '/toolkit',
  scanTool: '/toolkit/:toolId',
  findings: '/findings',
  scans: '/scans',
  reports: '/reports',
  reportsCompare: '/reports/compare',
  workflows: '/workflows',
  settings: '/settings',
  task: '/task/:taskId',
  signIn: '/signin',
} as const

export const routePath = {
  scanTool: (toolId: string) => `${routes.toolkit}/${encodeURIComponent(toolId)}`,
  task: (taskId: string) => `/task/${encodeURIComponent(taskId)}`,
} as const
