# Frontend-Backend Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all frontend-backend gaps found in the parity audit so every API endpoint is properly consumed by the frontend, and rebuild the frontend on port 8986.

**Architecture:** Seven targeted edits — 3 backend query fixes, 1 new Settings list page, navigation/routing updates, glossary refresh, and a frontend build+serve step.

**Tech Stack:** Python/FastAPI (backend), React/TypeScript/Tailwind (frontend), Vite (build), pytest (backend tests)

---

### Task 1: Add settings search to search API

**Files:**
- Modify: `src/api/routes/search.py:9-58`
- Modify: `tests/test_api/test_search.py`

**Step 1: Write the failing test**

Add to `tests/test_api/test_search.py`:

```python
def test_search_returns_settings(client, populated_db):
    """Test search returns settings key in response."""
    response = client.get("/api/search?q=assignments")
    assert response.status_code == 200
    data = response.json()

    assert "settings" in data


def test_search_finds_settings_by_name(client, populated_db):
    """Test search finds feature settings by name."""
    # First insert a setting to find
    import sqlite3
    conn = sqlite3.connect(populated_db)
    conn.execute("""
        INSERT INTO feature_settings (setting_id, feature_id, name, description, status)
        VALUES ('test_setting', 'assignments', 'Assignment Redesign', 'New assignment UI', 'active')
    """)
    conn.commit()
    conn.close()

    response = client.get("/api/search?q=Redesign")
    data = response.json()

    assert len(data["settings"]) >= 1
    assert data["settings"][0]["setting_id"] == "test_setting"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api/test_search.py -v`
Expected: 2 FAIL — `settings` key missing from response

**Step 3: Add settings search query to search.py**

In `src/api/routes/search.py`, after the content search block (line 52) and before the return (line 54), add:

```python
        # Search settings
        cursor.execute("""
            SELECT
                fs.setting_id, fs.name, fs.description,
                fs.feature_id,
                f.name as feature_name
            FROM feature_settings fs
            JOIN features f ON fs.feature_id = f.feature_id
            WHERE fs.name LIKE ? OR fs.description LIKE ?
            ORDER BY fs.name
            LIMIT 10
        """, (search_term, search_term))
        settings = rows_to_list(cursor.fetchall())
```

Update the return statement (line 54-58) to include settings:

```python
        return {
            "features": features,
            "options": options,
            "settings": settings,
            "content": content,
        }
```

Also update the empty-query early return (line 13) to include settings:

```python
        return {"features": [], "options": [], "settings": [], "content": []}
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api/test_search.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/api/routes/search.py tests/test_api/test_search.py
git commit -m "fix: add settings search to search API endpoint"
```

---

### Task 2: Add setting_id to release detail and dashboard announcements

**Files:**
- Modify: `src/api/routes/releases.py:82-94`
- Modify: `src/api/routes/dashboard.py:19-34`
- Modify: `tests/test_api/test_releases.py`
- Modify: `tests/test_api/test_dashboard.py`

**Step 1: Write the failing tests**

Add to `tests/test_api/test_releases.py`:

```python
def test_release_detail_announcements_include_setting_id(client, populated_db):
    """Test release detail announcements include setting_id field."""
    # Insert a setting-linked announcement
    import sqlite3
    conn = sqlite3.connect(populated_db)
    conn.execute("""
        INSERT INTO feature_settings (setting_id, feature_id, name, status)
        VALUES ('test_setting', 'gradebook', 'Gradebook Redesign', 'active')
    """)
    conn.execute("""
        INSERT INTO feature_announcements (feature_id, setting_id, content_id, h4_title, section, category, description, announced_at)
        VALUES ('gradebook', 'test_setting', 'deploy_note_2026-02-18', 'Gradebook Redesign', 'Bug Fixes', 'Gradebook', 'UI improvements', '2026-02-18 00:00:00')
    """)
    conn.commit()
    conn.close()

    response = client.get("/api/releases/deploy_note_2026-02-18")
    data = response.json()

    setting_announcements = [a for a in data["announcements"] if a.get("setting_id")]
    assert len(setting_announcements) >= 1
    assert setting_announcements[0]["setting_id"] == "test_setting"
```

Add to `tests/test_api/test_dashboard.py`:

```python
def test_dashboard_announcements_include_setting_id(client, populated_db):
    """Test dashboard announcements include setting_id field."""
    import sqlite3
    conn = sqlite3.connect(populated_db)
    conn.execute("""
        INSERT INTO feature_settings (setting_id, feature_id, name, status)
        VALUES ('dash_setting', 'gradebook', 'Dashboard Setting', 'active')
    """)
    conn.execute("""
        INSERT INTO feature_announcements (feature_id, setting_id, content_id, h4_title, section, category, description, announced_at)
        VALUES ('gradebook', 'dash_setting', 'release_note_2026-02-21', 'Dashboard Setting', 'Bug Fixes', 'Gradebook', 'Fix', '2026-02-21 00:00:00')
    """)
    conn.commit()
    conn.close()

    response = client.get("/api/dashboard")
    data = response.json()

    all_announcements = data["release_note"]["announcements"]
    setting_announcements = [a for a in all_announcements if a.get("setting_id")]
    assert len(setting_announcements) >= 1
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api/test_releases.py::test_release_detail_announcements_include_setting_id tests/test_api/test_dashboard.py::test_dashboard_announcements_include_setting_id -v`
Expected: 2 FAIL — setting_id not in announcement dicts

**Step 3: Add setting_id to both queries**

In `src/api/routes/releases.py`, update the release detail announcements query (line 82-94). Add `fa.setting_id,` after the `fa.description, fa.option_id,` line:

```sql
            SELECT
                fa.id, fa.h4_title, fa.anchor_id, fa.section, fa.category,
                fa.description, fa.option_id, fa.setting_id,
                fa.enable_location_account, fa.enable_location_course,
                COALESCE(fa.beta_date, fo.beta_date) as beta_date,
                COALESCE(fa.production_date, fo.production_date) as production_date,
                {announcement_status_sql()} as option_status
            FROM feature_announcements fa
            LEFT JOIN feature_options fo ON fa.option_id = fo.option_id
            WHERE fa.content_id = ?
            ORDER BY fa.section, fa.category, fa.h4_title
```

In `src/api/routes/dashboard.py`, update `_get_announcements()` (line 19-35). Add `fa.setting_id,` after the `fa.option_id,` line:

```sql
        SELECT
            fa.id,
            fa.h4_title,
            fa.section,
            fa.category,
            fa.description,
            fa.option_id,
            fa.setting_id,
            COALESCE(fa.beta_date, fo.beta_date) as beta_date,
            COALESCE(fa.production_date, fo.production_date) as production_date,
            {announcement_status_sql()} as option_status
        FROM feature_announcements fa
        LEFT JOIN feature_options fo ON fa.option_id = fo.option_id
        WHERE fa.content_id = ?
        ORDER BY fa.section, fa.category
```

**Step 4: Run all tests to verify they pass**

Run: `pytest tests/test_api/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/api/routes/releases.py src/api/routes/dashboard.py tests/test_api/test_releases.py tests/test_api/test_dashboard.py
git commit -m "fix: add setting_id to release detail and dashboard announcement queries"
```

---

### Task 3: Create Settings list page

**Files:**
- Create: `frontend/src/pages/Settings.tsx`

**Step 1: Create Settings.tsx**

This follows the exact same pattern as `frontend/src/pages/Options.tsx`. Create `frontend/src/pages/Settings.tsx`:

```tsx
import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { settingsApi } from '../api/client'
import type { FeatureSetting } from '../types'
import StatusFilter from '../components/StatusFilter'
import SortSelect from '../components/SortSelect'
import StatusPill, { DatePill } from '../components/StatusPill'
import { SearchIcon, XMarkIcon, ArrowRightIcon, CogIcon } from '../components/icons'

const SETTING_STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'beta', label: 'Beta', color: 'bg-status-beta' },
  { value: 'active', label: 'Released', color: 'bg-status-released' },
  { value: 'pending', label: 'Pending', color: 'bg-status-pending' },
  { value: 'deprecated', label: 'Deprecated', color: 'bg-status-deprecated' },
]

export default function Settings() {
  const [searchParams, setSearchParams] = useSearchParams()
  const status = searchParams.get('status') || ''
  const sort = searchParams.get('sort') || 'updated'
  const [searchQuery, setSearchQuery] = useState('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['settings', { status, sort }],
    queryFn: () => settingsApi.list({ status: status || undefined, sort }),
    staleTime: 1000 * 60 * 5,
  })

  const updateParams = (updates: Record<string, string>) => {
    const newParams = new URLSearchParams(searchParams)
    Object.entries(updates).forEach(([key, value]) => {
      if (value) { newParams.set(key, value) } else { newParams.delete(key) }
    })
    setSearchParams(newParams)
  }

  const filteredSettings = useMemo(() => {
    if (!data?.settings) return []
    if (!searchQuery.trim()) return data.settings
    const query = searchQuery.toLowerCase()
    return data.settings.filter(setting => {
      const name = setting.name.toLowerCase()
      const desc = (setting.description || setting.meta_summary || '').toLowerCase()
      const feature = (setting.feature_name || '').toLowerCase()
      return name.includes(query) || desc.includes(query) || feature.includes(query)
    })
  }, [data?.settings, searchQuery])

  const totalCount = data?.settings?.length || 0

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-title text-zinc-100">Feature Settings</h1>
          <p className="mt-1 text-xs text-zinc-500 font-mono">
            {isLoading ? '...' : (
              searchQuery
                ? `${filteredSettings.length} of ${totalCount} settings`
                : `${totalCount} settings`
            )}
          </p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="space-y-3 mb-6">
        <div className="relative max-w-sm">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-600" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search settings..."
            className="w-full pl-9 pr-8 py-2 text-sm bg-surface-2 border border-zinc-800 rounded-md
                       text-zinc-300 placeholder:text-zinc-600 font-mono
                       focus:outline-none focus:border-zinc-600 focus-visible:ring-2 focus-visible:ring-signal-blue/40 transition-colors"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-400">
              <XMarkIcon className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <StatusFilter
            value={status}
            onChange={(newStatus) => updateParams({ status: newStatus })}
            options={SETTING_STATUS_OPTIONS}
          />
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-zinc-400">sort</span>
            <SortSelect value={sort} onChange={(newSort) => updateParams({ sort: newSort })} />
          </div>
        </div>
      </div>

      {/* Settings table */}
      <div className="card overflow-hidden">
        {/* Table header */}
        <div className="px-4 py-2.5 border-b border-zinc-800/50 flex items-center gap-4 text-xs font-mono uppercase tracking-widest text-zinc-400">
          <span className="w-20">Status</span>
          <span className="flex-1">Name</span>
          <span className="hidden sm:block w-28">Feature</span>
          <span className="hidden md:block w-24">Prod Date</span>
          <span className="w-4" />
        </div>

        {isLoading ? (
          Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="data-row">
              <div className="w-20"><div className="skeleton h-4 w-14 rounded" /></div>
              <div className="flex-1"><div className="skeleton h-4 w-48" /></div>
              <div className="hidden sm:block w-28"><div className="skeleton h-3 w-20" /></div>
            </div>
          ))
        ) : isError ? (
          <div className="p-8 text-center">
            <p className="text-signal-red text-sm">Failed to load settings</p>
          </div>
        ) : filteredSettings.length === 0 ? (
          <div className="p-8 text-center">
            <CogIcon className="w-6 h-6 mx-auto text-zinc-700" />
            <p className="mt-2 text-sm text-zinc-500">No settings found</p>
            {(status || searchQuery) && (
              <button
                onClick={() => { setSearchQuery(''); updateParams({ status: '' }) }}
                className="mt-3 text-xs font-mono text-signal-blue hover:text-signal-blue/80"
              >
                clear filters
              </button>
            )}
          </div>
        ) : (
          filteredSettings.map((setting) => (
            <SettingRow key={setting.setting_id} setting={setting} />
          ))
        )}
      </div>
    </div>
  )
}

function SettingRow({ setting }: { setting: FeatureSetting }) {
  return (
    <Link to={`/settings/${setting.setting_id}`} className="data-row group">
      <div className="w-20 flex-shrink-0">
        <StatusPill status={setting.status} size="sm" showDot={false} />
      </div>

      <div className="flex-1 min-w-0">
        <span className="text-sm text-zinc-300 group-hover:text-white transition-colors truncate block">
          {setting.name}
        </span>
      </div>

      <div className="hidden sm:block w-28 flex-shrink-0">
        {setting.feature_name && (
          <span className="text-xs font-mono text-zinc-500 truncate block">
            {setting.feature_name}
          </span>
        )}
      </div>

      <div className="hidden md:flex items-center w-24 flex-shrink-0">
        <DatePill label="P" date={setting.production_date} variant="prod" />
      </div>

      <ArrowRightIcon className="w-3.5 h-3.5 text-zinc-600 group-hover:text-zinc-400 transition-colors flex-shrink-0" />
    </Link>
  )
}
```

**Step 2: Verify no TypeScript errors**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors related to Settings.tsx (may have pre-existing warnings)

**Step 3: Commit**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "feat: add Settings list page with filtering and sorting"
```

---

### Task 4: Update navigation and routing

**Files:**
- Modify: `frontend/src/App.tsx:1-34`
- Modify: `frontend/src/components/Layout.tsx:1-159`

**Step 1: Update App.tsx**

Add the import for Settings at the top (after line 11 — the Glossary import):

```tsx
import Settings from './pages/Settings'
```

Add the `/settings` route after the `/options/:optionId` route (line 20), and replace the `/options` redirect (line 27) with a direct route:

The routes block should look like:

```tsx
<Route index element={<Dashboard />} />
<Route path="registry" element={<Registry />} />
<Route path="features/:featureId" element={<FeatureDetail />} />
<Route path="options" element={<Options />} />
<Route path="options/:optionId" element={<OptionDetail />} />
<Route path="settings" element={<Settings />} />
<Route path="settings/:settingId" element={<SettingDetail />} />
<Route path="releases" element={<Releases />} />
<Route path="releases/:contentId" element={<ReleaseDetail />} />
<Route path="announcements/:id" element={<AnnouncementDetail />} />
<Route path="glossary" element={<Glossary />} />
{/* Redirects from old routes */}
<Route path="features" element={<Navigate to="/registry" replace />} />
```

Note: The existing `Options` import is already present (line 13 of the original does NOT import Options — you need to add it). Check if `Options` is imported; if not, add `import Options from './pages/Options'`.

**Step 2: Update Layout.tsx navigation**

Update `navLinks` array (line 10-15) to:

```tsx
  const navLinks = [
    { path: '/', label: 'Dashboard' },
    { path: '/registry', label: 'Registry' },
    { path: '/options', label: 'Options' },
    { path: '/settings', label: 'Settings' },
    { path: '/releases', label: 'Releases' },
    { path: '/glossary', label: 'Glossary' },
  ]
```

Update `isActive` function (line 17-26) to handle the new paths:

```tsx
  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    if (path === '/registry') {
      return location.pathname.startsWith('/registry')
        || location.pathname.startsWith('/features/')
    }
    return location.pathname.startsWith(path)
  }
```

Note: Remove `/options/` and `/settings/` from the registry isActive check — those now have their own nav items.

**Step 3: Update footer version**

In Layout.tsx, change the footer version (line 133):

```tsx
canvas/tracker <span className="text-zinc-500">v2.1</span>
```

**Step 4: Verify no TypeScript errors**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`

**Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Layout.tsx
git commit -m "feat: add Options and Settings to navigation bar"
```

---

### Task 5: Update Glossary lifecycle stages

**Files:**
- Modify: `frontend/src/pages/Glossary.tsx:12-55`

**Step 1: Update the Lifecycle Stages section**

Replace the content inside `<Section title="Lifecycle Stages">` (lines 13-55) with:

```tsx
        <Section title="Lifecycle Stages">
          <div className="card p-5 space-y-4">
            <p className="text-sm text-zinc-400 leading-relaxed">
              Feature <strong className="text-zinc-300">options</strong> (admin toggles) progress through lifecycle stages.
              Feature <strong className="text-zinc-300">settings</strong> (automatic changes) use date-based statuses instead.
            </p>

            <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 pt-2">
              Feature Option Stages
            </h3>
            <dl className="space-y-4">
              <Definition
                term="Preview"
                color="text-status-preview"
              >
                In active development. Has user groups for feedback. Will eventually graduate to Optional.
              </Definition>
              <Definition
                term="Optional"
                color="text-status-optional"
              >
                Released and available for admin configuration. Admins can enable or disable at account or course level.
                Most features stay here permanently.
              </Definition>
            </dl>

            <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 pt-2">
              Enforcement
            </h3>
            <dl className="space-y-4">
              <Definition
                term="Will Be Enforced"
                color="text-amber-400"
              >
                An optional feature that Instructure has flagged for future enforcement.
                The toggle will eventually be removed and the feature enabled for everyone
                (e.g., New Quizzes replacing Classic Quizzes).
              </Definition>
            </dl>

            {/* Visual progression */}
            <div className="pt-4 border-t border-zinc-800/50">
              <p className="text-xs font-mono text-zinc-500 mb-3">Progression</p>
              <div className="flex items-center gap-2 flex-wrap text-sm font-mono">
                <span className="px-2.5 py-1 rounded-md bg-status-preview/15 text-status-preview">Preview</span>
                <Arrow />
                <span className="px-2.5 py-1 rounded-md bg-status-optional/15 text-status-optional">Optional</span>
                <Arrow />
                <div className="flex items-center gap-1">
                  <span className="px-2.5 py-1 rounded-md bg-status-optional/15 text-status-optional">Optional</span>
                  <span className="px-1.5 py-0.5 text-xs rounded bg-amber-400/15 text-amber-400">Enforced</span>
                </div>
                <Arrow />
                <span className="px-2.5 py-1 rounded-md bg-surface-3 text-zinc-500">Removed</span>
              </div>
              <p className="mt-3 text-xs text-zinc-500">
                Not all features follow every stage. Many stay optional permanently.
              </p>
            </div>

            <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 pt-2">
              Feature Setting Statuses
            </h3>
            <dl className="space-y-4">
              <Definition term="Pending" color="text-status-pending">
                Announced but neither beta nor production date has arrived.
              </Definition>
              <Definition term="Beta" color="text-status-beta">
                Available on the beta environment for testing.
              </Definition>
              <Definition term="Released" color="text-status-released">
                Production date has passed. Active in production for all users.
              </Definition>
            </dl>
          </div>
        </Section>
```

**Step 2: Verify no TypeScript errors**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`

**Step 3: Commit**

```bash
git add frontend/src/pages/Glossary.tsx
git commit -m "fix: update Glossary lifecycle stages to match current data model"
```

---

### Task 6: Build frontend and serve on port 8986

**Step 1: Install dependencies (if needed)**

Run: `cd frontend && npm install`

**Step 2: Build the frontend**

Run: `cd frontend && npm run build`
Expected: Build completes with output in `frontend/dist/`

**Step 3: Kill any existing server on port 8986**

Run: `powershell -Command "Get-NetTCPConnection -State Listen -LocalPort 8986 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"`

**Step 4: Start the server**

Run: `cd /c/Users/mclea/claude/canvas-rss && python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8986`
Expected: Server starts, serves API at `/api/*` and frontend at `/`

**Step 5: Verify the frontend loads**

Open `http://localhost:8986` in a browser or use curl:
- `curl -s http://localhost:8986/api/health` → `{"status":"healthy"}`
- `curl -s http://localhost:8986/ | head -5` → HTML with React app

**Step 6: Run full backend test suite**

Run: `pytest tests/test_api/ -v`
Expected: All tests pass

**Step 7: Commit build output (if tracked)**

The `frontend/dist/` directory may be gitignored. If so, no commit needed for build output. Just verify the server is running.
