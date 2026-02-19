# Frontend-Backend Parity Audit & Fix

**Date:** 2026-02-18
**Status:** Design approved

## Problem

After multiple backend schema changes (v2.0 → v2.1 → will_be_enforced boolean), several frontend-backend gaps have accumulated:

1. Search API doesn't return settings results
2. Release detail announcements missing setting_id
3. No standalone Settings list page
4. Options page exists but is inaccessible (redirects to registry)
5. Glossary lifecycle stages stale
6. Footer version outdated

## Design

### 1. Backend Fixes

**`src/api/routes/search.py`:**
- Add feature_settings search query (by name, description)
- Return `settings` key in response

**`src/api/routes/releases.py`:**
- Add `fa.setting_id` to release detail announcements query (get_release_detail)

**`src/api/routes/dashboard.py`:**
- Add `fa.setting_id` to `_get_announcements()` query

### 2. New Settings List Page

Create `frontend/src/pages/Settings.tsx` following Options.tsx pattern:
- Search box (filter by name/description/feature)
- Status filter (beta, released, deprecated)
- Sort options (updated, alphabetical, beta_date, production_date)
- Table rows: StatusPill, name, feature name, production date
- Links to `/settings/:settingId`

### 3. Navigation & Routing

**`frontend/src/components/Layout.tsx`:**
- Add "Options" and "Settings" to navLinks array
- Nav order: Dashboard | Feature Registry | Options | Settings | Release History | Glossary
- Update isActive() for /options and /settings paths
- Footer version: v2.0 → v2.1

**`frontend/src/App.tsx`:**
- Remove `/options` redirect to `/registry`
- Add `/settings` route pointing to new Settings page
- Import Settings page

### 4. Glossary Update

**`frontend/src/pages/Glossary.tsx`:**
- Update lifecycle stages to match actual values:
  - Preview (feature_preview) - in active development
  - Optional - stable, admin can enable/disable
  - Will Be Enforced badge - optional features scheduled for enforcement
- Update visual progression: Preview → Optional → Optional + Will Be Enforced → Enforced (removed)

### Files Changed

| File | Type | Change |
|------|------|--------|
| `src/api/routes/search.py` | Edit | Add settings search |
| `src/api/routes/releases.py` | Edit | Add setting_id to query |
| `src/api/routes/dashboard.py` | Edit | Add setting_id to query |
| `frontend/src/pages/Settings.tsx` | New | Settings list page |
| `frontend/src/App.tsx` | Edit | Routes + import |
| `frontend/src/components/Layout.tsx` | Edit | Nav + footer |
| `frontend/src/pages/Glossary.tsx` | Edit | Lifecycle stages |
