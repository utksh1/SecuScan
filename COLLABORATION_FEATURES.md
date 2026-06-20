# Collaboration Features Implementation Guide

## Overview
This document describes the team collaboration features added to SecuScan, enabling security teams to comment on findings, assign work, track status, and share insights.

## Features Implemented

### 1. Comments & Annotations
Users can add textual comments/annotations to any finding for contextual analysis and discussion.

**Database**: `comments` table
- `id`: Unique comment identifier
- `finding_id`: Reference to the finding
- `user_id`: Who wrote the comment (derived from X-User-Id header)
- `content`: Comment text (required, max 5000 chars)
- `created_at`, `updated_at`: Timestamps

**API Endpoints**:
- `POST /api/v1/finding/{finding_id}/comments` - Create comment
  - Body: `{ "content": "Your comment here" }`
  - Returns: Full comment object
  - **Side effects**: Creates activity record, notifies assigned user if present

- `GET /api/v1/finding/{finding_id}/comments` - List comments
  - Returns: Array of comments ordered chronologically (oldest first)

**Frontend Components**:
- `CommentsPanel.tsx` - Toggleable panel showing comments in chronological order + composer

---

### 2. Assignment System
Findings can be assigned to team members for ownership and accountability.

**Database Extensions**: `findings` table
- `assigned_to`: User ID of assignee (TEXT, nullable)
- `assigned_by`: User ID who made the assignment (TEXT, nullable)

**API Endpoints**:
- `POST /api/v1/finding/{finding_id}/assign` - Assign finding
  - Body: `{ "assigned_to": "user:alice" }`
  - Returns: Assignment details with timestamp
  - **Side effects**:
    - Updates finding's `assigned_to` and `assigned_by` columns
    - Creates activity record
    - Generates notification for assignee

**Frontend Components**:
- `AssignmentControl.tsx` - Display current assignee, allow reassignment with inline editing

---

### 3. Status Workflow
Track findings through their lifecycle: OPEN → IN_PROGRESS → RESOLVED (and back).

**Database Extensions**: `findings` table
- `status`: One of 'OPEN', 'IN_PROGRESS', 'RESOLVED' (defaults to 'OPEN')

**API Endpoints**:
- `POST /api/v1/finding/{finding_id}/status` - Update status
  - Body: `{ "status": "IN_PROGRESS" }`
  - Returns: Old status, new status, timestamp
  - **Side effects**:
    - Updates finding's `status` column
    - Creates activity record with before/after details
    - Notifies assignee of status change

**Frontend Components**:
- `StatusSelector.tsx` - Button row showing current status + clickable transitions

---

### 4. Sharing Controls
Control who can access each finding: PRIVATE (owner only), TEAM (same workspace), or PUBLIC (all authenticated users).

**Database Extensions**: `findings` table
- `visibility`: One of 'PRIVATE', 'TEAM', 'PUBLIC' (defaults to 'PRIVATE')

**API Endpoints**:
- `POST /api/v1/finding/{finding_id}/visibility` - Update visibility
  - Body: `{ "visibility": "TEAM" }`
  - Returns: Old visibility, new visibility, timestamp
  - **Side effects**:
    - Updates finding's `visibility` column
    - Creates activity record

**Frontend Components**:
- `VisibilityControl.tsx` - Expandable dropdown with descriptions

---

### 5. Notification System
In-app notifications alert users to important events: assignments, comments, status changes.

**Database**: `notifications` table
- `id`: Unique notification ID
- `user_id`: Target recipient (derived from X-User-Id)
- `finding_id`: Related finding (nullable for system notifications)
- `action_type`: Event type ('comment_added', 'finding_assigned', 'status_changed', etc.)
- `message`: Human-readable message
- `is_read`: Boolean flag
- `metadata_json`: Contextual data (e.g., who commented, new status)
- `created_at`: Timestamp

**API Endpoints**:
- `GET /api/v1/notifications` - List notifications
  - Query params: `?is_read=false&limit=50&offset=0`
  - Returns: Paginated notification list

- `POST /api/v1/notification/{notification_id}/mark-read` - Mark as read
  - Returns: Notification with is_read=true

**Frontend Components**:
- (To implement) `NotificationsBell.tsx` - Header icon showing unread count + dropdown list

---

### 6. Activity Feed / Audit Trail
Every action on a finding is recorded chronologically for transparency and compliance.

**Database**: `activities` table
- `id`: Unique activity record ID
- `finding_id`: Related finding
- `user_id`: Who performed the action
- `action`: Event type ('comment_added', 'finding_assigned', 'status_changed', 'visibility_changed')
- `details_json`: Before/after values or contextual data
- `timestamp`: When the action occurred

**API Endpoints**:
- `GET /api/v1/finding/{finding_id}/activity` - Retrieve activity trail
  - Query params: `?limit=50&offset=0`
  - Returns: Paginated list of activities (newest first)

**Frontend Components**:
- `ActivityFeed.tsx` - Timeline view with icons, user info, action descriptions, and timestamps

---

## Database Schema

### Migration File: `backend/secuscan/migrations/007_add_collaboration.sql`

Creates three new tables:

```sql
CREATE TABLE comments (
    id TEXT PRIMARY KEY,
    finding_id TEXT NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    finding_id TEXT REFERENCES findings(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE activities (
    id TEXT PRIMARY KEY,
    finding_id TEXT NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    timestamp TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);
```

Extends `findings` table with:
```sql
ALTER TABLE findings ADD COLUMN assigned_to TEXT;
ALTER TABLE findings ADD COLUMN assigned_by TEXT;
ALTER TABLE findings ADD COLUMN status TEXT NOT NULL DEFAULT 'OPEN';
ALTER TABLE findings ADD COLUMN visibility TEXT NOT NULL DEFAULT 'PRIVATE';
```

---

## Backend Models

All models are defined in `backend/secuscan/models.py`:

```python
class FindingStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"

class FindingVisibility(str, Enum):
    PRIVATE = "PRIVATE"
    TEAM = "TEAM"
    PUBLIC = "PUBLIC"

class Comment(BaseModel):
    id: Optional[str] = None
    finding_id: str
    user_id: str
    content: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class CommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)

class NotificationResponse(BaseModel):
    id: str
    user_id: str
    finding_id: Optional[str] = None
    action_type: str
    message: str
    is_read: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

class ActivityResponse(BaseModel):
    id: str
    finding_id: str
    user_id: str
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime
```

The `Finding` model was extended with:
```python
assigned_to: Optional[str] = None
assigned_by: Optional[str] = None
status: FindingStatus = FindingStatus.OPEN
visibility: FindingVisibility = FindingVisibility.PRIVATE
```

---

## Authorization & Access Control

All endpoints enforce **ownership-based access control** using the existing `X-User-Id` header:

1. **Comment Creation/Listing**: Only owner can comment on or view comments for their finding
2. **Assignment**: Only owner can assign their findings
3. **Status Updates**: Only owner can change status
4. **Visibility Changes**: Only owner can change visibility
5. **Notifications**: Each user sees only their own notifications
6. **Activity Feed**: Only owner can view activity for their findings

The owner is resolved via `auth.resolve_owner_id()` which:
- Reads `X-User-Id` header
- Converts it to `user:{header_value}` format
- Stores as `owner_id` in all records

---

## Testing

Comprehensive integration tests in `testing/backend/integration/`:

**test_comments.py**
- Comment creation and validation
- Chronological ordering
- Access control (non-owner blocked)
- Activity creation on comment
- Notification to assignee

**test_assignments.py**
- Basic assignment
- Reassignment tracking
- Activity records for assignments
- Assignee notifications
- Multiple reassignments

**test_status_notifications.py**
- All status transitions
- Activity creation for status changes
- Notifications to assignee
- Notification read/unread filtering
- Multiple status changes tracked

Run tests:
```bash
cd /workspaces/SecuScan
python -m pytest testing/backend/integration/test_comments.py -v
python -m pytest testing/backend/integration/test_assignments.py -v
python -m pytest testing/backend/integration/test_status_notifications.py -v
```

---

## Frontend Integration

### Adding Collaboration Components to Finding Detail View

In `frontend/src/pages/Findings.tsx`, within the finding detail pane:

```typescript
import CommentsPanel from '../components/CommentsPanel'
import AssignmentControl from '../components/AssignmentControl'
import StatusSelector from '../components/StatusSelector'
import VisibilityControl from '../components/VisibilityControl'
import ActivityFeed from '../components/ActivityFeed'

// Inside the component:
const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null)
const [commentsPanelOpen, setCommentsPanelOpen] = useState(false)
const [activityFeedOpen, setActivityFeedOpen] = useState(false)

// In the JSX:
{selectedFinding && (
  <div className="collaboration-section">
    <AssignmentControl
      findingId={selectedFinding.id}
      assignedTo={selectedFinding.assigned_to}
      assignedBy={selectedFinding.assigned_by}
      onAssignmentChange={(user) => {
        setSelectedFinding({...selectedFinding, assigned_to: user})
      }}
    />

    <StatusSelector
      findingId={selectedFinding.id}
      currentStatus={selectedFinding.status}
      onStatusChange={(status) => {
        setSelectedFinding({...selectedFinding, status})
      }}
    />

    <VisibilityControl
      findingId={selectedFinding.id}
      currentVisibility={selectedFinding.visibility}
      onVisibilityChange={(visibility) => {
        setSelectedFinding({...selectedFinding, visibility})
      }}
    />

    <CommentsPanel
      findingId={selectedFinding.id}
      isOpen={commentsPanelOpen}
      onToggle={() => setCommentsPanelOpen(!commentsPanelOpen)}
    />

    <ActivityFeed
      findingId={selectedFinding.id}
      isOpen={activityFeedOpen}
      onToggle={() => setActivityFeedOpen(!activityFeedOpen)}
    />
  </div>
)}
```

### Creating NotificationsBell Component (Future)

```typescript
// frontend/src/components/NotificationsBell.tsx
export default function NotificationsBell() {
  const [notifications, setNotifications] = useState<NotificationAlert[]>([])
  const [unreadCount, setUnreadCount] = useState(0)

  // Load notifications on mount
  // Show unread count in bell icon
  // Dropdown to mark as read
  // Link to finding from notification
}
```

---

## Migration & Deployment

1. **Database Migration**: On next startup, the backend automatically:
   - Runs migrations in `backend/secuscan/migrations/`
   - Creates `comments`, `notifications`, `activities` tables
   - Adds new columns to `findings` table
   - Creates indexes for query performance

2. **API Versioning**: All new endpoints are under `/api/v1/` (no breaking changes)

3. **Backward Compatibility**:
   - Existing finding queries still work
   - New fields have sensible defaults
   - No changes to existing endpoint contracts

---

## Files Modified

### Backend
- `backend/secuscan/models.py` — Added enums and new models
- `backend/secuscan/database.py` — Added migration logic for new columns
- `backend/secuscan/routes.py` — Implemented 8 new endpoints
- `backend/secuscan/migrations/007_add_collaboration.sql` — ✨ NEW

### Frontend
- `frontend/src/api.ts` — Added 8 client functions
- `frontend/src/components/CommentsPanel.tsx` — ✨ NEW
- `frontend/src/components/AssignmentControl.tsx` — ✨ NEW
- `frontend/src/components/StatusSelector.tsx` — ✨ NEW
- `frontend/src/components/VisibilityControl.tsx` — ✨ NEW
- `frontend/src/components/ActivityFeed.tsx` — ✨ NEW

### Tests
- `testing/backend/integration/test_comments.py` — ✨ NEW
- `testing/backend/integration/test_assignments.py` — ✨ NEW
- `testing/backend/integration/test_status_notifications.py` — ✨ NEW

---

## Next Steps

1. ✅ Backend implementation complete
2. ✅ Unit tests created
3. ⏳ **Integrate components into Finding detail page** (UI/UX refinement)
4. ⏳ **Create NotificationsBell for header** (notifications inbox)
5. ⏳ **Run full test suite and address any failures**
6. ⏳ **Deploy and gather team feedback**

---

## Support & Questions

- All authorization checks use existing `X-User-Id` header mechanism
- No external service dependencies (all in-database)
- Activity trail is immutable and comprehensive
- Notifications are user-scoped; no cross-user visibility
