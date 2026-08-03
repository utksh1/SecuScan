export interface CheatSheetFlag {
  flag: string;
  description: string;
}

export interface CheatSheet {
  toolId: string;
  toolName: string;
  overview: string;
  flags: CheatSheetFlag[];
  ethicalTip: string;
}

const toolCheatSheets: Record<string, CheatSheet> = {
  nmap: {
    toolId: "nmap",
    toolName: "Nmap",
    overview:
      "Nmap (Network Mapper) is an open-source tool for network discovery and security auditing. " +
      "It sends raw IP packets to discover hosts, open ports, running services, and OS fingerprints.",
    flags: [
      { flag: "-sn", description: "Ping sweep — discover live hosts without port scanning." },
      { flag: "-sV", description: "Service version detection — identify software on each port." },
      { flag: "-sC", description: "Run default NSE scripts for common vulnerability checks." },
      { flag: "-p-", description: "Scan all 65,535 TCP ports instead of the default top-1000." },
      { flag: "-A",  description: "Aggressive scan: OS detection, version, scripts, traceroute." },
      { flag: "-T4", description: "Timing template 4 (aggressive) — faster on reliable networks." },
      { flag: "-oN", description: "Save output in normal human-readable format to a file." },
    ],
    ethicalTip:
      "Always confirm written authorization before scanning. Even a ping sweep can trigger IDS alerts " +
      "and may be illegal on networks you do not own.",
  },

  nikto: {
    toolId: "nikto",
    toolName: "Nikto",
    overview:
      "Nikto is an open-source web server scanner that checks for dangerous files, outdated server software, " +
      "and common misconfigurations across more than 6,700 potentially dangerous items.",
    flags: [
      { flag: "-h",       description: "Target host or IP address to scan." },
      { flag: "-p",       description: "Specify a non-default port (e.g., -p 8443)." },
      { flag: "-ssl",     description: "Force SSL/HTTPS mode for the connection." },
      { flag: "-Tuning",  description: "Select test categories (1=Files, 4=XSS, 9=SQL injection)." },
      { flag: "-o",       description: "Write scan results to an output file." },
      { flag: "-Format",  description: "Output format: txt, csv, xml, or html." },
      { flag: "-timeout", description: "Set per-request timeout in seconds for slow targets." },
    ],
    ethicalTip:
      "Nikto is intentionally noisy and will appear in web server logs. Only run it against targets " +
      "you have explicit written permission to test.",
  },

  sqlmap: {
    toolId: "sqlmap",
    toolName: "SQLMap",
    overview:
      "SQLMap is an automated SQL injection and database takeover tool. It detects and exploits SQL injection " +
      "flaws in web applications, then extracts or manipulates the underlying database.",
    flags: [
      { flag: "-u",        description: "Target URL with injectable parameter." },
      { flag: "--dbs",     description: "Enumerate all databases after confirming injection." },
      { flag: "-D/-T/-C",  description: "Specify database, table, and column to extract." },
      { flag: "--dump",    description: "Dump contents of the selected table or column." },
      { flag: "--level",   description: "Test intensity 1–5; higher checks more injection points." },
      { flag: "--risk",    description: "Risk level 1–3; higher may modify data — use with caution." },
      { flag: "--batch",   description: "Non-interactive mode; accepts all defaults automatically." },
    ],
    ethicalTip:
      "SQLMap with --dump can exfiltrate real user data. Only run it in controlled lab environments " +
      "or against targets with explicit written authorization.",
  },
};

export default toolCheatSheets;