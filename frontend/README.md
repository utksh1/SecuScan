# SecuScan Frontend

React-based web interface for the SecuScan pentesting toolkit.

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
│   │   ├── Layout.jsx       # Main app layout with sidebar
│   │   ├── ConsentModal.jsx # Consent confirmation dialog
│   │   ├── DynamicForm.jsx  # Form generator from plugin schema
│   │   └── TaskCard.jsx     # Task display card
│   │
│   ├── pages/               # Route components
│   │   ├── Scanner.jsx      # Main scanning interface
│   │   ├── TaskHistory.jsx  # Task history list
│   │   ├── TaskDetails.jsx  # Individual task view
│   │   └── Settings.jsx     # Settings page
│   │
│   ├── context/             # React Context for state
│   │   └── AppContext.jsx   # Global app state
│   │
│   ├── services/            # API integration
│   │   └── api.js           # Backend API client
│   │
│   ├── App.jsx              # Main app component with routing
│   ├── App.css              # App-specific styles
│   ├── main.jsx             # React entry point
│   └── index.css            # Global styles
│
├── index.html               # HTML template
├── vite.config.js           # Vite configuration
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
- `api.js` abstracts backend communication
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
```jsx
// src/pages/MyPage.jsx
export default function MyPage() {
  return <div>My Page Content</div>
}
```

2. Add route in `App.jsx`:
```jsx
<Route path="/mypage" element={<MyPage />} />
```

3. Add navigation link in `Layout.jsx`:
```jsx
<NavLink to="/mypage">My Page</NavLink>
```

### Adding a New Component

1. Create component in `src/components/`:
```jsx
// src/components/MyComponent.jsx
export default function MyComponent({ prop1, prop2 }) {
  return <div>{prop1} - {prop2}</div>
}
```

2. Import and use:
```jsx
import MyComponent from '../components/MyComponent'

<MyComponent prop1="value" prop2={123} />
```

### API Integration

Add new endpoints in `src/services/api.js`:
```javascript
export const api = {
  // ... existing methods
  
  myNewEndpoint: (param) => request(`/my-endpoint/${param}`, {
    method: 'POST',
    body: JSON.stringify({ data: 'value' })
  })
}
```

Use in components:
```jsx
import { api } from '../services/api'

async function handleAction() {
  try {
    const result = await api.myNewEndpoint('param')
    console.log(result)
  } catch (error) {
    console.error(error.message)
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
2. Check Vite proxy in `vite.config.js`:
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

## 📦 Deployment

### Build for Production

```bash
# Install dependencies
npm install

# Create production build
npm run build
```

Output in `dist/` directory.

### Serve with Backend

Option 1: **Static File Serving**
```python
# In backend/main.py
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

Option 2: **Separate Web Server**
```bash
# Serve frontend with nginx/caddy/apache
# Point backend API calls to backend server
```

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
