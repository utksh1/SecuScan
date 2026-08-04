export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export function downloadFile(content: string, filename: string, contentType: string): void {
  downloadBlob(new Blob([content], { type: contentType }), filename)
}

/** Filename the backend also sets on Content-Disposition, rebuilt client-side
 *  because that header is not readable in cross-origin deployments. */
export function findingsExportFilename(extension: string, now: Date = new Date()): string {
  return `secuscan_findings_${now.toISOString().split('T')[0]}.${extension}`
}
