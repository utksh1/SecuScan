import asyncio
import os
import sys

from secuscan.config import settings
from secuscan.database import init_db, get_db
from secuscan.models import WebhookConfig
from secuscan.notifications import test_webhook_config, notify_scan_completion

async def main():
    await init_db()
    
    config = WebhookConfig(
        custom_url="http://httpbin.org/post"
    )
    print("Testing webhook test_webhook_config...")
    await test_webhook_config(config)
    print("Test passed.")
    
    print("Testing notify_scan_completion...")
    await notify_scan_completion(
        task_id="test_task_123",
        target="example.com",
        status="completed",
        duration=42.5,
        findings_summary={"high": 2, "medium": 5},
        config=config
    )
    print("Notify passed.")

if __name__ == "__main__":
    asyncio.run(main())
