export interface ToolData {
  title: string;
  overview: string;
  flags: { flag: string; description: string }[];
  ethical_tip: string;
}

export const learningData: Record<string, ToolData> = {
  nmap: {
    title: "Nmap (Network Mapper)",
    overview: "Nmap is an open-source tool used for network discovery and vulnerability scanning. It sends packets to target hosts and analyzes responses to identify active devices and open ports.",
    flags: [
      { flag: "-sV", description: "Service Version Detection. Probes open ports to determine what software/version is running." },
      { flag: "-p-", description: "Scans all 65,535 ports instead of just the default top 1,000 ports." },
      { flag: "-O", description: "OS Detection. Attempts to guess the operating system running on the target." }
    ],
    ethical_tip: "Aggressive scanning can overwhelm older network hardware or fragile legacy systems. Always secure explicit permission before scanning networks."
  },
  nikto: {
    title: "Nikto Web Scanner",
    overview: "Nikto is a dedicated web server scanner that tests web servers for thousands of dangerous files, outdated software versions, and server configuration vulnerabilities.",
    flags: [
      { flag: "-h", description: "Target Host. Specifies the target web server's URL, IP address, or hostname." },
      { flag: "-Tuning", description: "Scan Tuning. Restricts the scan to specific vulnerability types to save time." }
    ],
    ethical_tip: "Nikto does not hide its traffic. It creates a vast amount of web server log entries, making it easily detectable by standard firewalls."
  },
  sqlmap: {
    title: "SQLMap Automatic Injection Tool",
    overview: "SQLMap automates the complex process of detecting and exploiting SQL injection flaws in web applications to take control of database servers.",
    flags: [
      { flag: "-u", description: "Target URL. The vulnerable address or form endpoint you want to test." },
      { flag: "--dbs", description: "Enumerate Databases. Lists all available databases on the remote management system." }
    ],
    ethical_tip: "SQL exploitation can easily lead to data corruption or complete leaks. Never test production databases without isolated backups."
  }
};