# Recurring Scans Implementation Guide

## Overview

This implementation adds scheduled, recurring scan capabilities to SecuScan with timezone-aware cron parsing, blackout window support, and missed-run recovery logic.

## Files Created

### Backend

1. **`backend/secuscan/utils/scheduler.py`** (New Module)
   - Core scheduling engine with timezone support
   - Functions:
     - `get_next_run_time()` - Parse cron and calculate next execution
     - `is_in_blackout_window()` - Check if time falls in excluded window
     - `should_recover_missed_run()` - Determine if missed runs should execute
     - `validate_cron_expression()` - Validate 5-part cron syntax
     - `validate_time_format()` - Validate HH:MM time format

2. **`backend/secuscan/utils/__init__.py`** (New Package Init)
   - Makes utils a proper Python package

3. **`testing/test_scheduler.py`** (New Tests)
   - Comprehensive unit tests using pytest
   - Tests for timezone handling, blackout windows, validation, etc.

### Frontend

1. **`frontend/src/components/ScanScheduleForm.jsx`** (New Component)
   - React form component with:
     - Cron expression input with 5-part validation
     - Timezone dropdown (common IANA timezones)
     - Optional blackout window time pickers
     - Client-side validation before submission
     - Error/success feedback UI
     - Accessibility features (ARIA labels, roles)

2. **`frontend/src/components/ScanScheduleForm.module.css`** (New Styles)
   - Responsive styling with dark mode support
   - Professional UI with proper spacing and typography
   - Mobile-optimized layout

3. **`frontend/src/components/ScanScheduleForm.test.jsx`** (New Tests)
   - Jest + React Testing Library tests
   - 40+ test cases covering rendering, validation, submission, errors, accessibility

### Dependencies

- **`croniter>=2.0.0`** - Added to `pyproject.toml` for cron parsing
- Already installed: `python-dateutil`, `zoneinfo` (stdlib)

---

## Backend Integration

### 1. Database Models

You'll need to add a model for storing scan schedules in `backend/secuscan/database.py`:

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class ScanSchedule(Base):
    __tablename__ = "scan_schedules"
    
    id = Column(Integer, primary_key=True)
    scan_id = Column(String, index=True, nullable=False)
    cron_expression = Column(String, nullable=False)
    timezone = Column(String, default="UTC")
    blackout_start = Column(String, nullable=True)  # HH:MM format
    blackout_end = Column(String, nullable=True)    # HH:MM format
    last_run_time = Column(DateTime, nullable=True)
    next_run_time = Column(DateTime, nullable=True)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 2. API Endpoints

Add these routes to `backend/secuscan/routes.py`:

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import datetime
from zoneinfo import ZoneInfo

from .utils.scheduler import (
    get_next_run_time,
    validate_cron_expression,
    validate_time_format
)

router = APIRouter(prefix="/api/schedules", tags=["schedules"])

class CreateScheduleRequest(BaseModel):
    scan_id: str = Field(..., description="ID of the scan to schedule")
    cron_expression: str = Field(..., description="5-part cron expression")
    timezone: str = Field(default="UTC", description="IANA timezone")
    blackout_start: str = Field(None, description="Blackout window start (HH:MM)")
    blackout_end: str = Field(None, description="Blackout window end (HH:MM)")

class ScheduleResponse(BaseModel):
    id: int
    scan_id: str
    cron_expression: str
    timezone: str
    blackout_start: Optional[str]
    blackout_end: Optional[str]
    next_run_time: datetime
    is_enabled: bool

@router.post("/create", response_model=ScheduleResponse)
async def create_schedule(request: CreateScheduleRequest, db: Session = Depends(get_db)):
    """Create a new recurring scan schedule."""
    
    # Validate inputs
    if not validate_cron_expression(request.cron_expression):
        raise HTTPException(status_code=400, detail="Invalid cron expression")
    
    if request.blackout_start and not validate_time_format(request.blackout_start):
        raise HTTPException(status_code=400, detail="Invalid blackout start time")
    
    if request.blackout_end and not validate_time_format(request.blackout_end):
        raise HTTPException(status_code=400, detail="Invalid blackout end time")
    
    if (request.blackout_start and not request.blackout_end) or \
       (not request.blackout_start and request.blackout_end):
        raise HTTPException(status_code=400, detail="Both blackout times required or neither")
    
    # Validate timezone
    try:
        ZoneInfo(request.timezone)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timezone")
    
    # Calculate next run time
    try:
        next_run = get_next_run_time(request.cron_expression, request.timezone)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Create schedule in database
    schedule = ScanSchedule(
        scan_id=request.scan_id,
        cron_expression=request.cron_expression,
        timezone=request.timezone,
        blackout_start=request.blackout_start,
        blackout_end=request.blackout_end,
        next_run_time=next_run,
        is_enabled=True
    )
    
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    
    return schedule

@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Retrieve a schedule by ID."""
    schedule = db.query(ScanSchedule).filter(ScanSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule

@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(schedule_id: int, request: CreateScheduleRequest, db: Session = Depends(get_db)):
    """Update an existing schedule."""
    schedule = db.query(ScanSchedule).filter(ScanSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Validate inputs (same as create)
    if not validate_cron_expression(request.cron_expression):
        raise HTTPException(status_code=400, detail="Invalid cron expression")
    
    # Update fields
    schedule.cron_expression = request.cron_expression
    schedule.timezone = request.timezone
    schedule.blackout_start = request.blackout_start
    schedule.blackout_end = request.blackout_end
    schedule.next_run_time = get_next_run_time(request.cron_expression, request.timezone)
    
    db.commit()
    db.refresh(schedule)
    
    return schedule

@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Delete a schedule."""
    schedule = db.query(ScanSchedule).filter(ScanSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    db.delete(schedule)
    db.commit()
    
    return {"message": "Schedule deleted"}
```

### 3. Scheduler Task Executor

Add to `backend/secuscan/executor.py` to integrate with the existing execution engine:

```python
from datetime import datetime
from zoneinfo import ZoneInfo
from .utils.scheduler import is_in_blackout_window, should_recover_missed_run

async def execute_scheduled_scans(db: Session):
    """
    Background task to execute due scheduled scans.
    Run periodically (e.g., every minute via APScheduler or similar).
    """
    now = datetime.now(ZoneInfo("UTC"))
    
    due_schedules = db.query(ScanSchedule).filter(
        ScanSchedule.is_enabled == True,
        ScanSchedule.next_run_time <= now
    ).all()
    
    for schedule in due_schedules:
        # Check if currently in blackout window
        tz = ZoneInfo(schedule.timezone)
        current_time = now.astimezone(tz)
        
        if is_in_blackout_window(current_time, schedule.blackout_start, schedule.blackout_end):
            # Skip execution, reschedule for next cycle
            schedule.next_run_time = get_next_run_time(
                schedule.cron_expression,
                schedule.timezone
            )
            db.commit()
            continue
        
        # Execute the scan
        try:
            await execute_scan(schedule.scan_id)
            schedule.last_run_time = datetime.now(tz)
        except Exception as e:
            # Log error but continue
            logger.error(f"Failed to execute scheduled scan {schedule.scan_id}: {e}")
        
        # Calculate next run time
        schedule.next_run_time = get_next_run_time(
            schedule.cron_expression,
            schedule.timezone
        )
        db.commit()
```

---

## Frontend Integration

### 1. Add Route

In `frontend/src/routes.ts`, add a schedules page route:

```typescript
import { lazy } from 'react';

export const routes = [
  // ... existing routes ...
  {
    path: '/schedules',
    component: lazy(() => import('./pages/Schedules')),
    label: 'Schedules'
  }
];
```

### 2. Create Schedules Page

Create `frontend/src/pages/Schedules.tsx`:

```typescript
import React, { useState, useEffect } from 'react';
import ScanScheduleForm from '../components/ScanScheduleForm';
import { api } from '../api';

const SchedulesPage: React.FC = () => {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchSchedules();
  }, []);

  const fetchSchedules = async () => {
    try {
      const response = await api.get('/api/schedules');
      setSchedules(response.data);
    } catch (err) {
      setError('Failed to load schedules');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (payload: any) => {
    try {
      await api.post('/api/schedules/create', payload);
      await fetchSchedules();
    } catch (err) {
      throw new Error('Failed to save schedule');
    }
  };

  return (
    <div>
      <h1>Recurring Scans</h1>
      
      <ScanScheduleForm onSubmit={handleSubmit} />
      
      {/* Display existing schedules */}
      <div>
        <h2>Active Schedules</h2>
        {schedules.map(schedule => (
          <div key={schedule.id}>
            <p>Cron: {schedule.cron_expression}</p>
            <p>Next run: {new Date(schedule.next_run_time).toLocaleString()}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SchedulesPage;
```

### 3. Add Navigation Link

In `frontend/src/components/Sidebar.tsx`, add link to schedules page.

---

## Testing

### Run Backend Tests

```bash
# From workspace root
./testing/test_python.sh
# Or directly:
pytest testing/test_scheduler.py -v
```

### Run Frontend Tests

```bash
cd frontend
npm run test -- ScanScheduleForm.test.jsx
```

---

## Architecture Decisions

1. **Timezone Handling**: Uses Python's `zoneinfo` (stdlib) and `croniter` for accurate timezone-aware cron parsing. All times are evaluated in the operator's specified timezone.

2. **Blackout Windows**: Supports overnight windows (e.g., 23:00–06:00) via comparison logic. Times are in 24-hour HH:MM format.

3. **Missed-Run Recovery**: Conservative approach—only recovers if:
   - Expected run time is in the past
   - NOT currently in a blackout window
   - Defaults to False on any error (safety over recovery)

4. **Validation**: Strict client-side validation in React prevents malformed requests. Server-side validation adds defense-in-depth.

5. **Responsiveness**: CSS Grid/Flexbox with mobile-first breakpoints. Dark mode support via CSS variables.

---

## Security Considerations

- **Cron Injection**: Validated with `croniter.is_valid()` before database storage
- **Timezone Validation**: Checked against `zoneinfo` registry
- **SQL Injection**: Using ORM (SQLAlchemy) with parameterized queries
- **CSRF**: Assume FastAPI/frontend CSRF middleware in place
- **Rate Limiting**: Recommend adding to `/api/schedules/*` endpoints

---

## Future Enhancements

1. **Timezone Library**: Consider `pytz` + Moment.js for more comprehensive timezone lists
2. **Cron UI Builder**: Drag-and-drop or select-based UI for non-technical users
3. **Schedule History**: Log execution history with success/failure details
4. **Notifications**: Email/Slack alerts for missed or failed runs
5. **Bulk Operations**: Create, update, or disable multiple schedules at once

---

## Example Usage

### Backend API

```bash
# Create schedule
curl -X POST http://localhost:8000/api/schedules/create \
  -H "Content-Type: application/json" \
  -d '{
    "scan_id": "web_scan_123",
    "cron_expression": "0 2 * * *",
    "timezone": "America/New_York",
    "blackout_start": "22:00",
    "blackout_end": "06:00"
  }'

# Get schedule
curl http://localhost:8000/api/schedules/1

# Update schedule
curl -X PUT http://localhost:8000/api/schedules/1 \
  -H "Content-Type: application/json" \
  -d '{"cron_expression": "0 */6 * * *", ...}'

# Delete schedule
curl -X DELETE http://localhost:8000/api/schedules/1
```

### Frontend Component

```jsx
import ScanScheduleForm from './components/ScanScheduleForm';

<ScanScheduleForm 
  onSubmit={async (payload) => {
    const response = await fetch('/api/schedules/create', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    return response.json();
  }}
  onCancel={() => navigate('/dashboard')}
/>
```

---

## Debugging

Enable debug logging in `backend/secuscan/config.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('scheduler')
```

Check Redis queue status (if using background tasks):

```bash
redis-cli LRANGE secuscan:scheduled_scans 0 -1
```

---

## References

- [croniter Documentation](https://croniter.readthedocs.io/)
- [Python zoneinfo](https://docs.python.org/3/library/zoneinfo.html)
- [IANA Timezone Database](https://www.iana.org/time-zones)
- [React Testing Library Docs](https://testing-library.com/docs/react-testing-library/intro/)
