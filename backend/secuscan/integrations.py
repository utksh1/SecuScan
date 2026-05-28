import httpx
import logging
from typing import Dict, Any
from .models import Finding

logger = logging.getLogger(__name__)

async def create_jira_ticket(finding: Finding, config: Dict[str, str]) -> Dict[str, Any]:
    url = config.get("jiraUrl", "").rstrip("/")
    email = config.get("jiraEmail")
    token = config.get("jiraToken")
    project_key = config.get("jiraProject")

    if not all([url, email, token, project_key]):
        raise ValueError("Missing Jira configuration parameters")

    api_url = f"{url}/rest/api/2/issue"

    description = f"""
*Target:* {finding.target}
*Severity:* {finding.severity}
*Category:* {finding.category}
*Discovered At:* {finding.discovered_at}

*Description:*
{finding.description}

*Remediation:*
{finding.remediation}
"""
    if finding.cve:
        description += f"\n*CVE:* {finding.cve}"

    payload = {
        "fields": {
            "project": {
                "key": project_key
            },
            "summary": f"[{finding.severity.upper()}] {finding.title}",
            "description": description,
            "issuetype": {
                "name": "Bug"
            }
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            api_url,
            json=payload,
            auth=(email, token),
            headers={"Content-Type": "application/json"}
        )

        if response.status_code >= 400:
            logger.error(f"Jira API error: {response.text}")
            raise Exception(f"Failed to create Jira ticket: {response.status_code} {response.text}")

        data = response.json()
        return {
            "ticket_id": data.get("key"),
            "ticket_url": f"{url}/browse/{data.get('key')}"
        }


async def create_github_issue(finding: Finding, config: Dict[str, str]) -> Dict[str, Any]:
    token = config.get("githubToken")
    repo = config.get("githubRepo")

    if not all([token, repo]):
        raise ValueError("Missing GitHub configuration parameters")

    api_url = f"https://api.github.com/repos/{repo}/issues"

    body = f"""
**Target:** `{finding.target}`
**Severity:** {finding.severity.upper()}
**Category:** {finding.category}
**Discovered At:** {finding.discovered_at}

### Description
{finding.description}

### Remediation
{finding.remediation}
"""
    if finding.cve:
        body += f"\n**CVE:** {finding.cve}"

    payload = {
        "title": f"[{finding.severity.upper()}] {finding.title}",
        "body": body,
        "labels": ["bug", "security"]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            api_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
        )

        if response.status_code >= 400:
            logger.error(f"GitHub API error: {response.text}")
            raise Exception(f"Failed to create GitHub issue: {response.status_code} {response.text}")

        data = response.json()
        return {
            "ticket_id": str(data.get("number")),
            "ticket_url": data.get("html_url")
        }
