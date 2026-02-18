# Canvas Feature Tracker Website - Design Document

**Created:** 2026-02-05
**Status:** Approved
**Author:** Brainstorming session

## Overview

A public website for educational technologists to track Canvas LMS feature options and deployment readiness. Serves as a "one stop shop" for central admins (decision makers) and divisional ed techs (local impact advisors) at U of T.

**Primary use case:** Assessing feature option deployment readiness and tracking upcoming changes.

## Pages & Navigation

### Site Structure

```
Dashboard (/)
├── Current Release Notes card
├── Current Deploy Notes card
├── Upcoming Changes timeline
├── Recent Activity feed (Q&A, Blog)
└── Date navigation (by publish date) + archive link

Features (/features)
├── Search/filter bar
├── Category filter (Core, Grading, Collaboration, etc.)
└── Feature cards grid (45 canonical features)

Feature Detail (/features/:feature_id)
├── Feature description (LLM-generated)
├── Associated feature options list
├── Recent announcements
└── Related community posts

Options (/options)
├── Search bar
├── Filters (status, feature, sort)
└── Feature option cards/list

Option Detail (/options/:option_id)
├── Meta summary (LLM-generated deployment readiness)
├── Deployment status + visual timeline
├── Configuration details
├── Community activity
└── Announcement history

Archive (/releases)
├── Type filter (Release/Deploy)
├── Year filter
├── Search
└── Grouped by month

Release/Deploy Detail (/releases/:content_id)
├── Full LLM summary
├── Features listed with lifecycle dates
└── Links to option detail pages
```

### Header Navigation

- Logo/title: "Canvas Feature Tracker"
- Nav links: Dashboard | Features | Options
- Global search bar (searches features, options, content)

## Dashboard Design

### Date Navigation

- Date selector navigates by **Instructure publish date** (when release/deploy notes were published)
- Previous/Next arrows step between release cycles
- "Current" badge indicates viewing latest
- URL updates for shareability: `/?date=2026-02-21`

### Layout (Three-Column Cards)

```
┌─────────────────────┬─────────────────────┬─────────────────┐
│   RELEASE NOTES     │    DEPLOY NOTES     │    UPCOMING     │
│   Published date    │    Published date   │    CHANGES      │
│                     │                     │                 │
│   [LLM Summary]     │    [LLM Summary]    │   ⚠️ Mar 21     │
│                     │                     │   deadline...   │
│   • Feature 1       │    • Fix 1          │                 │
│     Beta · Prod     │    • Fix 2          │   • Apr 18      │
│   • Feature 2       │    • Fix 3          │   deadline...   │
│                     │                     │                 │
│   [View full]       │    [View full]      │   [View all]    │
│   [Browse archive]  │    [Browse archive] │                 │
└─────────────────────┴─────────────────────┴─────────────────┘
```

### Lifecycle Date Display

Individual features within release notes show beta/production dates:

```
Document Processing App
Beta Mar 1  ·  Prod Mar 15      ← subtle status pills

Accessibility Checker
Available now                    ← soft green indicator
```

### Recent Activity Feed

Below cards, shows recent Q&A and blog post activity with timestamps.

## Features Page Design

### Grid Layout

Cards for each of 45 canonical features showing:
- Feature name
- Count of associated feature options
- Quick status summary (e.g., "2 in beta", "all stable")

### Filtering

- Search by name
- Filter by category:
  - Core Course Features
  - Grading & Assessment
  - Collaboration
  - Communication
  - Administration
  - Add-on Products

## Feature Detail Page Design

Shows when clicking a canonical feature from the grid.

**Sections:**
1. **Header** - Feature name, category, LLM description
2. **Feature Options** - List of associated options with status pills
3. **Recent Announcements** - Latest feature_announcements
4. **Related Community** - Q&A/blog posts via content_feature_refs

## Options Page Design

### List View

Each option row shows:
- Option name (canonical_name)
- Parent feature (linked)
- Lifecycle status pill (Preview / Optional / Default On / Released)
- Beta/Prod dates if applicable
- LLM description snippet (1-2 lines)

### Filtering & Sorting

**Filters:**
- Status: All, Pending, Preview, Optional, Default On, Released
- Feature: Dropdown of 45 canonical features

**Sort options:**
- Recently updated
- Alphabetical
- Beta date (soonest)
- Prod date (soonest)

## Option Detail Page Design

The comprehensive view for evaluating a feature option.

**Sections:**

### 1. Header
- Option name (canonical_name)
- Parent feature (linked)
- Status pill
- Meta summary (LLM-generated 3-4 sentence deployment readiness)

### 2. Deployment Status
- Beta date
- Production date
- First seen date
- Visual timeline: Announced → Beta → Prod → Released

### 3. Configuration
- Account setting (Disabled/Unlocked, etc.)
- Course setting
- Subaccount configuration (Yes/No)
- Permissions
- Affected areas (list)
- Affects UI (Yes/No)
- Link to Feature Preview user group

### 4. Community Activity
- Linked Q&A posts with LLM implications
- Linked blog posts with LLM implications
- "View all" link

### 5. Announcement History
Chronological list of feature_announcements:
- Date + source (Release Notes)
- H4 title
- LLM summary
- Section + Category

## Archive Page Design

### List View

Grouped by month, showing:
- Title (e.g., "Canvas Release Notes (2026-02-21)")
- Type badge (Release / Deploy)
- Feature/fix count
- Preview of features mentioned

### Filters
- Type: All, Release Notes, Deploy Notes
- Year dropdown
- Search

### Full Note View

When clicking an archive item:
- Back link
- Title + publish date
- Link to original on Instructure
- Full LLM summary
- Features grouped by section (New Features, Updated Features)
- Each feature links to its Option Detail page

## Technical Architecture

### Stack

- **Frontend:** Vite + React 18 + TypeScript + TailwindCSS
- **Backend:** FastAPI (Python)
- **Database:** Existing SQLite with v2.0 schema
- **Deployment:** Single Docker container (FastAPI serves both API and static React build)

### API Endpoints

```
GET  /api/dashboard
     → current release note, deploy note, recent activity, upcoming changes

GET  /api/dashboard?date=2026-02-21
     → dashboard for specific publish date

GET  /api/features
     → list of canonical features with option counts/status summary

GET  /api/features/:feature_id
     → feature detail with options, announcements, community posts

GET  /api/options?status=preview&feature=speedgrader&sort=beta_date
     → filtered/sorted list of feature options

GET  /api/options/:option_id
     → full option detail (config, timeline, community, history)

GET  /api/releases?type=release&year=2026
     → archive list of release/deploy notes

GET  /api/releases/:content_id
     → full release/deploy note content with features

GET  /api/search?q=document+processor
     → global search across features, options, content
```

### Project Structure

```
canvas-rss/
├── docker-compose.yml        (updated)
├── src/
│   ├── api/                  (new FastAPI app)
│   │   ├── main.py           (FastAPI app, serves static + API)
│   │   └── routes/
│   │       ├── dashboard.py
│   │       ├── features.py
│   │       ├── options.py
│   │       ├── releases.py
│   │       └── search.py
│   └── ...existing scraper code...
├── frontend/                 (new React app)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       ├── pages/
│       ├── hooks/
│       └── types/
└── ...existing files...
```

### Deployment

Single container approach:
1. Build React app to `frontend/dist/`
2. FastAPI serves static files from `frontend/dist/`
3. API routes under `/api/`
4. All other routes serve React's `index.html` (client-side routing)

## Design Principles

### Visual Design
- **Spacious/scannable** - Generous whitespace, card-based layouts
- **Polished status indicators** - Subtle pills/badges, not buttons
- **Clean typography** - Clear hierarchy, readable at a glance
- **Consistent color palette** - Status colors (beta, prod, deprecated) used consistently

### Information Architecture
- **Date navigation by publish date** - Instructure's canonical reference
- **Lifecycle dates on features** - Beta/prod dates always visible
- **Drill-down pattern** - Dashboard → Features → Options → Detail
- **Multiple entry points** - Can start at Features or Options level

### User Experience
- **Public access** - No authentication required
- **Shareable URLs** - All views have bookmarkable URLs
- **Global search** - Find anything from anywhere
- **Responsive** - Works on desktop and tablet

## Data Dependencies

This design relies on the v2.0 database schema:

### Required Tables
- `features` - Canonical features with LLM descriptions
- `feature_options` - Options with lifecycle dates, meta_summary
- `feature_announcements` - H4-level announcements with implications
- `content_items` - Release notes, deploy notes, blog, Q&A
- `content_feature_refs` - Links content to features/options
- `content_comments` - For community sentiment

### Required Columns (v2.0)
- `feature_options.beta_date`, `production_date`, `deprecation_date`
- `feature_options.meta_summary`, `description`
- `feature_announcements.description`, `implications`
- `features.description`

## Next Steps

1. **Create implementation plan** - Break into tasks for API and frontend
2. **Set up frontend scaffolding** - Vite + React + TypeScript + Tailwind
3. **Build API layer** - FastAPI routes reading from existing database
4. **Build frontend pages** - Using frontend-design skill for polished UI
5. **Integrate and deploy** - Update Docker configuration
