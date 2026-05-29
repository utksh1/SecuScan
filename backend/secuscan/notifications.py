import httpx
import logging
import asyncio
from typing import Dict, Any
from .models import WebhookConfig

logger = logging.getLogger(__name__)

async def _send_with_retry(url: str, payload: Dict[str, Any], headers: Dict[str, str] = None, max_retries: int = 3):
    """Send an HTTP request with exponential backoff retry logic."""
    if not headers:
        headers = {"Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                if response.status_code < 400:
                    return response
                logger.warning(f"Webhook request to {url} failed with status {response.status_code}. Attempt {attempt+1}/{max_retries}")
            except httpx.RequestError as e:
                logger.warning(f"Webhook request to {url} failed: {e}. Attempt {attempt+1}/{max_retries}")

            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)

        logger.error(f"Failed to send webhook to {url} after {max_retries} attempts.")

async def send_slack_webhook(url: str, payload: Dict[str, Any]):
    await _send_with_retry(url, payload)

async def send_discord_webhook(url: str, payload: Dict[str, Any]):
    await _send_with_retry(url, payload)

async def send_custom_webhook(url: str, payload: Dict[str, Any]):
    await _send_with_retry(url, payload)


async def test_webhook_config(config: WebhookConfig):
    payload = {
        "text": "This is a test notification from SecuScan.",
        "content": "This is a test notification from SecuScan.",
        "message": "This is a test notification from SecuScan."
    }

    tasks = []
    if config.slack_url:
        tasks.append(send_slack_webhook(config.slack_url, {"text": payload["text"]}))
    if config.discord_url:
        tasks.append(send_discord_webhook(config.discord_url, {"content": payload["content"]}))
    if config.custom_url:
        tasks.append(send_custom_webhook(config.custom_url, payload))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    else:
        raise ValueError("No webhook URLs provided to test.")

async def notify_scan_completion(task_id: str, target: str, status: str, duration: float, findings_summary: Dict[str, int], config: WebhookConfig):
    duration_str = f"{duration:.2f}s" if duration else "Unknown"

    severity_text = ", ".join(f"{k}: {v}" for k, v in findings_summary.items() if v > 0)
    if not severity_text:
        severity_text = "No findings"

    text_content = (
        f"🎯 *Scan Completed*\n"
        f"Target: `{target}`\n"
        f"Status: {status.upper()}\n"
        f"Duration: {duration_str}\n"
        f"Findings: {severity_text}"
    )

    slack_payload = {
        "text": text_content
    }

    discord_payload = {
        "content": text_content.replace("*", "**") # Discord uses double asterisk for bold
    }

    custom_payload = {
        "task_id": task_id,
        "target": target,
        "status": status,
        "duration_seconds": duration,
        "findings_summary": findings_summary
    }

    tasks = []
    if config.slack_url:
        tasks.append(send_slack_webhook(config.slack_url, slack_payload))
    if config.discord_url:
        tasks.append(send_discord_webhook(config.discord_url, discord_payload))
    if config.custom_url:
        tasks.append(send_custom_webhook(config.custom_url, custom_payload))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
