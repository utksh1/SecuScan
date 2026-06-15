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
  docs: '/docs',
  support: '/support',
  privacyPolicy: '/privacy-policy',
  termsOfService: '/terms-of-service',
} as const

export const routePath = {
  scanTool: (toolId: string) => `${routes.toolkit}/${encodeURIComponent(toolId)}`,
  task: (taskId: string) => `/task/${encodeURIComponent(taskId)}`,
} as const