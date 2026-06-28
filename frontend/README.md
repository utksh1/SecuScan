# SecuScan Frontend

React-based web interface for the SecuScan pentesting toolkit.
<p align="center">
  <img src="Favicon-SecuScan.png" alt="Favicon" width="120"/>
</p>

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- SecuScan backend running on `http://127.0.0.1:8080`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will start on `http://localhost:3000` with hot module replacement enabled.

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

---

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── AppShell.tsx     # Main app layout with sidebar
│   │   ├── ConsentModal.tsx # Consent confirmation dialog
│   │   ├── DynamicForm.tsx  # Form generator from plugin schema
│   │   └── TaskCard.tsx     # Task display card
│   │
│   ├── pages/               # Route components
│   │   ├── Scanner.tsx      # Main scanning interface
│   │   ├── Scans.tsx        # Task history list
│   │   ├── TaskDetails.tsx  # Individual task view
│   │   └── Settings.tsx     # Settings page
│   │
│   ├── context/             # React Context for state
│   │   └── AppContext.tsx   # Global app state
│   │
│   ├── services/            # API integration
│   │   └── api.ts           # Backend API client
│   │
│   ├── App.tsx              # Main app component with routing
│   ├── App.css              # App-specific styles
│   ├── main.tsx             # React entry point
│   └── index.css            # Global styles
│
├── index.html               # HTML template
├── vite.config.ts           # Vite configuration
├── package.json             # Dependencies
└── README.md                # This file
```

---

## 🎨 Architecture

### Technology Stack

- **Framework:** React 18
- **Build Tool:** Vite 5
- **Router:** React Router v6
- **State:** React Context + Hooks
- **Styling:** CSS Modules (vanilla CSS)
- **API:** Fetch API

### Design Patterns

#### 1. **Component-Based Architecture**
- Small, reusable components
- Props for configuration
- Separation of concerns

#### 2. **Context for Global State**
- `AppContext` provides plugins and settings
- Avoids prop drilling
- Centralized data fetching

#### 3. **Service Layer**
- `api.ts` abstracts backend communication
- Consistent error handling
- Type-safe responses (via Pydantic backend)

#### 4. **Dynamic Form Generation**
- Forms generated from plugin metadata
- Supports conditional fields (`show_if`)
- Preset-based defaults

---

## 🔧 Key Features

### 1. **Plugin Selection**
Sidebar lists all available plugins fetched from backend:
```jsx
<Layout>  {/* Sidebar with plugin list */}
  <Scanner />  {/* Dynamic form for selected plugin */}
</Layout>
```

### 2. **Dynamic Forms**
Forms are generated from plugin schema metadata:
```json
{
  "fields": [
    {
      "name": "target",
      "type": "text",
      "label": "Target IP",
      "required": true,
      "placeholder": "192.168.1.1"
    }
  ]
}
```

Rendered as:
```jsx
<DynamicForm schema={schema} onSubmit={handleSubmit} />
```

### 3. **Consent Modal**
Before starting intrusive scans, users must confirm:
```jsx
<ConsentModal
  plugin={plugin}
  onConfirm={() => api.startTask(...)}
  onCancel={() => setShowConsent(false)}
/>
```

### 4. **Live Task Monitoring**
Task details page auto-refreshes every 2 seconds while task is running:
```jsx
useEffect(() => {
  const interval = setInterval(() => {
    if (task?.status === 'running') loadTask()
  }, 2000)
  return () => clearInterval(interval)
}, [task?.status])
```

### 5. **Task History**
Displays all tasks with filtering and auto-refresh:
```jsx
// Auto-refresh every 5 seconds
useEffect(() => {
  const interval = setInterval(loadTasks, 5000)
  return () => clearInterval(interval)
}, [])
```

---

## 🛠️ Development Guide

### Adding a New Page

1. Create component in `src/pages/`:
```tsx
// src/pages/MyPage.tsx
export default function MyPage() {
  return <div>My Page Content</div>
}
```

2. Add route in `App.tsx`:
```tsx
<Route path="/mypage" element={<MyPage />} />
```

3. Add navigation link in your layout component (e.g. `AppShell.tsx`):
```tsx
<NavLink to="/mypage">My Page</NavLink>
```

### Adding a New Component

1. Create component in `src/components/`:
```tsx
// src/components/MyComponent.tsx

type Props = {
  prop1: string;
  prop2: number;
};

const MyComponent = ({ prop1, prop2 }: Props): JSX.Element => {
  return <div>{prop1} - {prop2}</div>;
};

export default MyComponent;
```

2. Import and use:
```tsx
import MyComponent from '../components/MyComponent';

<MyComponent prop1="value" prop2={123} />
```

### API Integration

Add new endpoints in `src/services/api.ts`:
```ts
// src/services/api.ts

export const api = {
  myNewEndpoint: (param: string) =>
    request(`/my-endpoint/${param}`, {
      method: "POST",
      body: JSON.stringify({ data: "value" }),
    }),
};
```

Use in components:
```tsx
import { api } from "../services/api";

async function handleAction(): Promise<void> {
  try {
    const result = await api.myNewEndpoint("param");
    console.log(result);
  } catch (error: unknown) {
    if (error instanceof Error) {
      console.error(error.message);
    } else {
      console.error(error);
    }
  }
}
```

---

## 🎯 Component Reference

### `<Layout>`
Main app layout with sidebar navigation.

**Props:**
- `children` - Page content

**Usage:**
```jsx
<Layout>
  <Scanner />
</Layout>
```

---

### `<DynamicForm>`
Generates forms from plugin schema metadata.

**Props:**
- `schema` - Plugin schema object
- `preset` - Default preset ID (optional)
- `onSubmit` - Submit handler `(data) => void`
- `loading` - Disable form during submission

**Usage:**
```jsx
<DynamicForm
  schema={pluginSchema}
  onSubmit={(data) => console.log(data)}
  loading={false}
/>
```

**Output Format:**
```javascript
{
  preset: "quick",
  inputs: {
    target: "192.168.1.1",
    port: 80,
    verbose: true
  }
}
```

---

### `<ConsentModal>`
Confirmation dialog for scan consent.

**Props:**
- `plugin` - Plugin object
- `onConfirm` - Confirm handler
- `onCancel` - Cancel handler

**Usage:**
```jsx
<ConsentModal
  plugin={selectedPlugin}
  onConfirm={handleStartScan}
  onCancel={() => setShowModal(false)}
/>
```

---

### `<TaskCard>`
Display task information in a card.

**Props:**
- `task` - Task object

**Usage:**
```jsx
<TaskCard task={taskData} />
```

**Task Object:**
```javascript
{
  task_id: "abc123",
  plugin_name: "Nmap",
  preset: "quick",
  status: "running",
  created_at: "2025-10-29T12:00:00Z",
  finished_at: null
}
```

---

## 🔄 State Management

### AppContext

Global state provider for plugins and settings.

**Values:**
```javascript
{
  plugins: [],        // Array of plugin objects
  settings: {},       // System settings
  loading: false,     // Initial load state
  error: null,        // Error message
  reload: () => {}    // Reload function
}
```

**Usage:**
```jsx
import { useApp } from '../context/AppContext'

function MyComponent() {
  const { plugins, settings, loading } = useApp()

  if (loading) return <div>Loading...</div>

  return <div>{plugins.length} plugins</div>
}
```

---

## 🎨 Styling Guide

### CSS Classes

**Layout:**
- `.app` - Main app container (grid)
- `.sidebar` - Sidebar navigation
- `.main` - Main content area

**Components:**
- `.card` - Content card with border
- `.btn` - Primary button
- `.list` - Unstyled list
- `.log` - Terminal-style output

**Forms:**
- `label` - Form label
- `input, select` - Form inputs

**Utilities:**
- `.text-sm` - Small text (14px)
- `.text-xs` - Extra small (12px)
- `.text-muted` - Muted color
- `.mt-{1,2,3}` - Margin top
- `.mb-{1,2,3}` - Margin bottom
- `.flex` - Flexbox container
- `.grid` - Grid container

### Status Colors

```css
.status-pending   { background: #fef3c7; }
.status-running   { background: #dbeafe; }
.status-completed { background: #d1fae5; }
.status-failed    { background: #fee2e2; }
.status-cancelled { background: #e5e7eb; }
```

---
## Available Commands

All commands must be run from the `frontend/` directory.

| Command | Description |
|---|---|
| `npm run dev` | Start the Vite development server |
| `npm run build` | Compile TypeScript and build for production |
| `npm run preview` | Preview the production build locally (port 8080) |
| `npm run typecheck` | Run TypeScript type checking without emitting files |
| `npm run test` | Run unit tests with Vitest |
| `npm run test:watch` | Run unit tests in watch mode (re-runs on file changes) |
| `npm run quality` | Run the quality gate checks |
| `npm run quality:full` | Run quality checks, typecheck, and tests together |
| `npm run e2e` | Run end-to-end tests with Playwright |
| `npm run e2e:ui` | Run end-to-end tests with Playwright's interactive UI |

---
## 🧪 Testing

### Manual Testing Checklist

- [ ] Can load plugin list from backend
- [ ] Can select a plugin and see its form
- [ ] Form fields match plugin schema
- [ ] Preset selection updates form defaults
- [ ] Consent modal appears before scan
- [ ] Task starts successfully
- [ ] Task details page updates in real-time
- [ ] Task history shows all tasks
- [ ] Can filter tasks by status
- [ ] Settings page loads correctly
- [ ] Navigation works between all pages
- [ ] Responsive design works on mobile


---
## ⚡ Frontend Checks Quickstart

Run all frontend commands from the `frontend/` directory.

### Install Dependencies

```bash
cd frontend
npm install
```

### Run Unit Tests

```bash
npm run test
```

### Run Tests in Watch Mode

```bash
npm run test:watch
```

### Run Type Checking

```bash
npm run typecheck
```

### Run Production Build

```bash
npm run build
```

### Run Quality Checks

```bash
npm run quality
```

### Run Full Quality Pipeline

```bash
npm run quality:full
```

### Run End-to-End Tests

```bash
npm run e2e
```

### Vitest Test File Locations

Vitest unit tests are located in:

```bash
frontend/testing/unit
```

Supported naming patterns include:

*.test.ts
*.test.tsx
*.spec.ts
*.spec.tsx

> Note for Windows users:
> Some npm scripts using `NODE_OPTIONS=...` may not run directly in PowerShell.

Run tests manually using:

```bash
npx vitest run
```

### Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

---

## 🐛 Troubleshooting

### Backend Connection Issues

**Error:** `Network error` or `Failed to fetch`

**Solution:**
1. Verify backend is running: `curl http://127.0.0.1:8000/api/v1/health`
2. Check Vite proxy in `vite.config.ts`:
```js
server: {
  proxy: {
    '/api': 'http://127.0.0.1:8000'
  }
}
```

### Plugin List Not Loading

**Error:** `Cannot read property 'plugins' of null`

**Solution:**
- Check AppContext initialization
- Verify `/api/v1/plugins` endpoint returns data
- Check browser console for API errors

### Form Not Submitting

**Error:** Task not starting

**Solution:**
1. Check all required fields are filled
2. Verify preset is selected
3. Check browser console for validation errors
4. Confirm consent modal was accepted

---

## 🏭 Production Deployment

### 1. Build the frontend

```bash
cd frontend
npm ci
npm run build
```

Output lands in `frontend/dist/`. Verify locally before deploying:

```bash
npm run preview
# Serves dist/ at http://127.0.0.1:8080
```

---

### 2. Set the API base URL at build time

The frontend resolves the backend URL via `src/api.ts::resolveApiBase()` in this priority order:

| Priority | Mechanism | When to use |
|----------|-----------|-------------|
| 1 | `VITE_API_BASE` env var | Production — always set this |
| 2 | Window location heuristic | Dev server on a non-5173 port |
| 3 | Vite proxy (`/api` → backend) | Local dev on port 5173 (default) |

**`VITE_API_BASE` must be set at build time**, not at runtime. Vite inlines `import.meta.env` values during the
build step — changing the env var after building has no effect.

```bash
VITE_API_BASE=http://your-backend-host:8081/api/v1 npm run build
```

Or create `frontend/.env.production`:
VITE_API_BASE=http://your-backend-host:8081/api/v1

> ⚠️ Do not confuse `VITE_API_BASE` (frontend, build-time) with `VITE_API_PROXY_TARGET` (Vite dev server only — has no effect in a production build).

---

### 3. Serve the built frontend

> ⚠️ `backend/secuscan/main.py` currently imports `StaticFiles` but does not mount the `dist/` directory. The backend cannot serve the frontend
> yet. Use one of the options below until that is wired up.

**Option A — nginx (recommended)**

```nginx
server {
    listen 80;
    root /path/to/frontend/dist;
    index index.html;

    # SPA fallback — required for React Router
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API calls to the backend
    location /api/ {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
    }
}
```

**Option B — quick local verification**

```bash
npx serve dist --single
# --single enables the SPA fallback for React Router
```

---

### 4. SPA route fallback — why it matters

SecuScan uses React Router for client-side navigation. If a user visits `/task/abc123` directly or refreshes the page on any route, the web
server looks for a real file at that path, finds nothing, and returns a **404**.

The fix is always the same: serve `index.html` for any path that does not match a real static file. The nginx `try_files` directive and
`serve --single` flag above both handle this. Without it, every direct link and browser refresh on a non-root route breaks.

---

### 5. Docker Compose note

The current `docker-compose.yml` runs the frontend service with `npm run dev` (Vite development server). This is intentional for
contributor workflows and is **not production-ready**. A multi-stage frontend Dockerfile is not yet present in the repository.

---

### Troubleshooting

**404 on page refresh or direct URL**
The SPA fallback is missing. Add `try_files $uri /index.html` to your nginx config or use `npx serve dist --single`.

**All API calls fail after deploying**
`VITE_API_BASE` was not set at build time. Rebuild with the correct value:
```bash
VITE_API_BASE=http://your-backend:8081/api/v1 npm run build
```

**`VITE_API_PROXY_TARGET` has no effect in production**
This variable only configures the Vite dev server proxy. It is completely ignored in the production build.

**CORS errors in the browser console**
Add your frontend's origin to the backend config in `.env`:
SECUSCAN_CORS_ALLOWED_ORIGINS=http://your-frontend-host

---

## 🔐 Security Considerations

1. **API Proxy:** Vite dev server proxies `/api` to backend
2. **No Secrets:** Frontend code is public - no API keys
3. **CORS:** Backend must allow your frontend origin in dev (default includes `localhost:5173` and `localhost:3000`)
4. **Localhost Only:** Both frontend and backend run locally

---

## 🚧 Future Enhancements

- [ ] Dark mode toggle
- [ ] Export task results (CSV/PDF)
- [ ] Real-time SSE streaming for live output
- [ ] WebSocket support for faster updates
- [ ] Toast notifications for actions
- [ ] Keyboard shortcuts
- [ ] Search/filter plugins
- [ ] Task comparison view
- [ ] Custom plugin upload

---

## 📄 License

MIT License - Same as SecuScan project

---

## 🙋 Support

For issues or questions:
1. Check backend is running correctly
2. Review browser console for errors
3. Verify API responses with curl/Postman
4. Check this README for common solutions

---

**Last Updated:** October 29, 2025
**Version:** 0.1.0-alpha
