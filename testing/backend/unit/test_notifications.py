import pytest

# ... existing imports ...

@pytest.mark.asyncio  # <--- THIS IS CRITICAL FOR ALL ASYNC CLASSES
class TestDeduplication:
    async def test_no_duplicate_first_notification(self, db):
        # ... your test code ...
        pass

@pytest.mark.asyncio
class TestDispatchNotification:
    async def test_dispatch_webhook(self, db):
        # ... your test code ...
        pass

@pytest.mark.asyncio
class TestProcessNotifications:
    async def test_process_critical_finding(self, db):
        # ... your test code ...
        pass

@pytest.mark.asyncio
class TestNotificationHistory:
    async def test_record_success_history(self, db):
        # ... your test code ...
        pass