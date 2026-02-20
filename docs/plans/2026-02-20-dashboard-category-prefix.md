# Dashboard Category Prefix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure dashboard AnnouncementRow to lead with tool category pill instead of status pill, matching the release detail page layout.

**Architecture:** Single component change in `Dashboard.tsx`. Replace the left-column StatusPill with a category pill, move dates and status pill into a bottom metadata row beneath the description.

**Tech Stack:** React, TypeScript, Tailwind CSS

---

### Task 1: Restructure AnnouncementRow component

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx:274-306`

**Step 1: Replace left column with category pill**

In `AnnouncementRow`, replace the status pill left column (lines 277-284) with a category pill:

```tsx
      {/* Category */}
      <div className="w-28 flex-shrink-0">
        <span className="pill bg-surface-3 text-zinc-500">
          {announcement.category || 'General'}
        </span>
      </div>
```

**Step 2: Add dates + status row beneath description**

Replace the current dates column (lines 299-303) with a metadata row inside the title/description div, after the description paragraph:

```tsx
      {/* Title, Description & Metadata */}
      <div className="flex-1 min-w-0">
        <Link
          to={`/announcements/${announcement.id}`}
          className="text-sm text-zinc-300 truncate block hover:text-white transition-colors"
        >
          {announcement.h4_title}
        </Link>
        {announcement.description && (
          <p className="text-xs text-zinc-500 mt-0.5 line-clamp-4">{announcement.description}</p>
        )}
        <div className="hidden sm:flex items-center gap-3 mt-1.5">
          <DatePill label="Beta" date={announcement.beta_date || null} variant="beta" />
          <DatePill label="Prod" date={announcement.production_date || null} variant="prod" />
          {announcement.option_status && (
            <StatusPill status={announcement.option_status} size="sm" showDot={false} />
          )}
        </div>
      </div>
```

**Step 3: Full replacement**

The complete `AnnouncementRow` function should become:

```tsx
function AnnouncementRow({ announcement }: { announcement: Announcement }) {
  return (
    <div className="data-row">
      {/* Category */}
      <div className="w-28 flex-shrink-0">
        <span className="pill bg-surface-3 text-zinc-500">
          {announcement.category || 'General'}
        </span>
      </div>

      {/* Title, Description & Metadata */}
      <div className="flex-1 min-w-0">
        <Link
          to={`/announcements/${announcement.id}`}
          className="text-sm text-zinc-300 truncate block hover:text-white transition-colors"
        >
          {announcement.h4_title}
        </Link>
        {announcement.description && (
          <p className="text-xs text-zinc-500 mt-0.5 line-clamp-4">{announcement.description}</p>
        )}
        <div className="hidden sm:flex items-center gap-3 mt-1.5">
          <DatePill label="Beta" date={announcement.beta_date || null} variant="beta" />
          <DatePill label="Prod" date={announcement.production_date || null} variant="prod" />
          {announcement.option_status && (
            <StatusPill status={announcement.option_status} size="sm" showDot={false} />
          )}
        </div>
      </div>
    </div>
  )
}
```

**Step 4: Visual verification**

Run: dev server should already be running on `http://localhost:8986`
Check: Dashboard shows category pills (Canvas Apps, New Quizzes, Assignments, etc.) on the left. Dates and status pill appear below description. Both Release Notes and Deploy Notes sections reflect the change.

**Step 5: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "style: lead dashboard announcements with category pill instead of status pill"
```
