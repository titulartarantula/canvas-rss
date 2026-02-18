# Release Display Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix four issues with release/deploy note display: rename "View on Canvas" to "View Online", make all announcement entries clickable with their own detail page, and increase description length from 1-2 to 3-5 sentences.

**Architecture:** New `/api/announcements/:id` backend endpoint joins `feature_announcements` with `content_items` and optionally `feature_options`/`feature_settings`. New `AnnouncementDetail.tsx` frontend page at `/announcements/:id`. Existing Dashboard and ReleaseDetail components updated to link all entries to announcement pages. LLM prompt updated for longer descriptions.

**Tech Stack:** FastAPI (Python), React + TypeScript, TanStack Query, Tailwind CSS, Google Gemini API

---

### Task 1: Rename "View on Canvas" to "View Online"

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx:249`
- Modify: `frontend/src/pages/ReleaseDetail.tsx:100`

**Step 1: Change text in Dashboard.tsx**

In `frontend/src/pages/Dashboard.tsx`, line 249, change:
```
View on Canvas
```
to:
```
View Online
```

**Step 2: Change text in ReleaseDetail.tsx**

In `frontend/src/pages/ReleaseDetail.tsx`, line 100, change:
```
view original
```
to:
```
View Online
```

**Step 3: Verify in browser**

Navigate to `http://localhost:8986` and confirm "View Online" appears in both the dashboard announcements tables and on a release detail page.

**Step 4: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/ReleaseDetail.tsx
git commit -m "fix: rename 'View on Canvas' to 'View Online'"
```

---

### Task 2: Add announcement detail API endpoint

**Files:**
- Modify: `src/api/routes/releases.py` (add new endpoint)

**Step 1: Add GET /api/announcements/{announcement_id} endpoint**

Add to `src/api/routes/releases.py` after the existing `get_release_detail` function:

```python
@router.get("/announcements/{announcement_id}")
def get_announcement_detail(announcement_id: int):
    """Get a single feature announcement with parent release and related option/setting info."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                fa.id, fa.h4_title, fa.anchor_id, fa.section, fa.category,
                fa.description, fa.option_id, fa.setting_id,
                fa.enable_location_account, fa.enable_location_course,
                COALESCE(fa.beta_date, fo.beta_date) as beta_date,
                COALESCE(fa.production_date, fo.production_date) as production_date,
                fo.status as option_status,
                fa.content_id,
                ci.title as release_title,
                ci.url as release_url,
                ci.content_type as release_type,
                fo.canonical_name as option_name,
                fo.name as option_display_name,
                fs.name as setting_name
            FROM feature_announcements fa
            JOIN content_items ci ON fa.content_id = ci.source_id
            LEFT JOIN feature_options fo ON fa.option_id = fo.option_id
            LEFT JOIN feature_settings fs ON fa.setting_id = fs.setting_id
            WHERE fa.id = ?
        """, (announcement_id,))
        row = row_to_dict(cursor.fetchone())

        if not row:
            raise HTTPException(status_code=404, detail="Announcement not found")

        return row
```

**Step 2: Test the endpoint manually**

```bash
curl http://localhost:8986/api/announcements/1 | python -m json.tool
```

Expected: JSON with announcement fields plus `release_title`, `release_url`, `content_id`, and optional `option_name`/`setting_name`.

**Step 3: Commit**

```bash
git add src/api/routes/releases.py
git commit -m "feat: add GET /api/announcements/:id endpoint"
```

---

### Task 3: Add frontend API client and TypeScript types

**Files:**
- Modify: `frontend/src/api/client.ts` (add `announcementsApi`)
- Modify: `frontend/src/types/index.ts` (add `AnnouncementDetail` type)

**Step 1: Add AnnouncementDetail type**

In `frontend/src/types/index.ts`, add after the `Announcement` interface:

```typescript
export interface AnnouncementDetail extends Announcement {
  anchor_id: string | null;
  content_id: string;
  release_title: string;
  release_url: string;
  release_type: string;
  option_name: string | null;
  option_display_name: string | null;
  setting_name: string | null;
}
```

**Step 2: Add announcementsApi to client**

In `frontend/src/api/client.ts`, add after the `releasesApi` object:

```typescript
export const announcementsApi = {
  get: async (id: number): Promise<AnnouncementDetail> => {
    const { data } = await api.get(`/announcements/${id}`);
    return data;
  },
};
```

Also add `AnnouncementDetail` to the import from `'../types'`.

**Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat: add announcement detail API client and types"
```

---

### Task 4: Create AnnouncementDetail page component

**Files:**
- Create: `frontend/src/pages/AnnouncementDetail.tsx`
- Modify: `frontend/src/App.tsx` (add route)

**Step 1: Create the page component**

Create `frontend/src/pages/AnnouncementDetail.tsx` following the same patterns as `ReleaseDetail.tsx` and `OptionDetail.tsx`:

```tsx
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { announcementsApi } from '../api/client'
import StatusPill, { DatePill } from '../components/StatusPill'
import {
  ChevronLeftIcon,
  ExternalLinkIcon,
  ArrowRightIcon,
} from '../components/icons'

export default function AnnouncementDetail() {
  const { id } = useParams<{ id: string }>()

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['announcement', id],
    queryFn: () => announcementsApi.get(Number(id)),
    enabled: !!id,
    staleTime: 1000 * 60 * 5,
  })

  if (isLoading) {
    return (
      <div className="animate-fade-in">
        <BackLink />
        <div className="mt-6">
          <div className="skeleton h-5 w-24 mb-3 rounded" />
          <div className="skeleton h-7 w-96 mb-3" />
          <div className="skeleton h-4 w-full mt-4" />
          <div className="skeleton h-4 w-3/4 mt-2" />
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="animate-fade-in">
        <BackLink />
        <div className="mt-6 card p-8 text-center">
          <p className="text-signal-red text-sm">Announcement not found</p>
          <p className="mt-1 text-xs text-zinc-500">
            {error instanceof Error ? error.message : 'The requested announcement could not be loaded.'}
          </p>
        </div>
      </div>
    )
  }

  const isDeployNote = data.release_type === 'deploy_note'
  const typeLabel = isDeployNote ? 'Deploy Note' : 'Release Note'

  // Build "View Online" URL: release_url + #anchor_id
  const onlineUrl = data.anchor_id
    ? `${data.release_url}#${data.anchor_id}`
    : data.release_url

  return (
    <div className="animate-fade-in">
      <BackLink contentId={data.content_id} releaseTitle={data.release_title} />

      <header className="mt-4">
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          {data.section && (
            <span className="pill bg-surface-3 text-zinc-400">{data.section}</span>
          )}
          {data.category && (
            <span className="pill bg-surface-3 text-zinc-500">{data.category}</span>
          )}
          {data.option_status && <StatusPill status={data.option_status} size="sm" showDot={false} />}
        </div>
        <h1 className="mt-3 text-title text-zinc-100 leading-tight">{data.h4_title}</h1>
        <div className="mt-2 flex items-center gap-4">
          <a
            href={onlineUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs font-mono text-signal-blue hover:text-signal-blue/80 transition-colors"
          >
            View Online <ExternalLinkIcon className="w-3 h-3" />
          </a>
          <span className="text-xs font-mono text-zinc-500">
            from {typeLabel}
          </span>
        </div>
      </header>

      {/* Description */}
      {data.description && (
        <div className="mt-6 card p-4">
          <p className="text-sm text-zinc-300 leading-relaxed">{data.description}</p>
        </div>
      )}

      {/* Dates */}
      <div className="mt-4 flex items-center gap-4">
        <DatePill label="Beta" date={data.beta_date || null} variant="beta" />
        <DatePill label="Prod" date={data.production_date || null} variant="prod" />
      </div>

      {/* Configuration details if available */}
      {(data.enable_location_account || data.enable_location_course) && (
        <div className="mt-6 card p-4">
          <p className="text-xs font-mono uppercase tracking-widest text-zinc-400 mb-3">Configuration</p>
          <div className="grid gap-2 text-xs font-mono">
            {data.enable_location_account && (
              <div className="flex justify-between">
                <span className="text-zinc-500">Account</span>
                <span className="text-zinc-300">{data.enable_location_account}</span>
              </div>
            )}
            {data.enable_location_course && (
              <div className="flex justify-between">
                <span className="text-zinc-500">Course</span>
                <span className="text-zinc-300">{data.enable_location_course}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Related Feature */}
      {(data.option_id || data.setting_id) && (
        <div className="mt-6 card p-4">
          <p className="text-xs font-mono uppercase tracking-widest text-zinc-400 mb-3">Related Feature</p>
          {data.option_id && (
            <Link
              to={`/options/${data.option_id}`}
              className="flex items-center justify-between group"
            >
              <span className="text-sm text-zinc-300 group-hover:text-white transition-colors">
                {data.option_name || data.option_display_name || data.option_id}
              </span>
              <ArrowRightIcon className="w-4 h-4 text-zinc-500 group-hover:text-zinc-300 transition-colors" />
            </Link>
          )}
          {!data.option_id && data.setting_id && (
            <Link
              to={`/settings/${data.setting_id}`}
              className="flex items-center justify-between group"
            >
              <span className="text-sm text-zinc-300 group-hover:text-white transition-colors">
                {data.setting_name || data.setting_id}
              </span>
              <ArrowRightIcon className="w-4 h-4 text-zinc-500 group-hover:text-zinc-300 transition-colors" />
            </Link>
          )}
        </div>
      )}
    </div>
  )
}

function BackLink({ contentId, releaseTitle }: { contentId?: string; releaseTitle?: string }) {
  if (contentId) {
    return (
      <Link
        to={`/releases/${contentId}`}
        className="inline-flex items-center gap-1 text-xs font-mono text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <ChevronLeftIcon className="w-3.5 h-3.5" />
        {releaseTitle || 'back to release'}
      </Link>
    )
  }
  return (
    <Link
      to="/"
      className="inline-flex items-center gap-1 text-xs font-mono text-zinc-500 hover:text-zinc-300 transition-colors"
    >
      <ChevronLeftIcon className="w-3.5 h-3.5" />
      dashboard
    </Link>
  )
}
```

**Step 2: Add route to App.tsx**

In `frontend/src/App.tsx`, add import and route:

```tsx
import AnnouncementDetail from './pages/AnnouncementDetail'
```

Add route after the releases route:
```tsx
<Route path="announcements/:id" element={<AnnouncementDetail />} />
```

**Step 3: Verify in browser**

Navigate to `http://localhost:8986/announcements/1` and confirm the page loads with announcement details.

**Step 4: Commit**

```bash
git add frontend/src/pages/AnnouncementDetail.tsx frontend/src/App.tsx
git commit -m "feat: add announcement detail page and route"
```

---

### Task 5: Update all announcement links to point to /announcements/:id

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx` (AnnouncementRow)
- Modify: `frontend/src/pages/ReleaseDetail.tsx` (AnnouncementCard)

**Step 1: Update Dashboard AnnouncementRow**

In `frontend/src/pages/Dashboard.tsx`, replace the `AnnouncementRow` function (lines 274-314). Change the link logic from option/setting routing to always link to `/announcements/:id`:

Replace:
```typescript
const detailLink = announcement.option_id
    ? `/options/${announcement.option_id}`
    : announcement.setting_id
      ? `/settings/${announcement.setting_id}`
      : null
  const TitleTag = detailLink ? Link : 'span'
  const titleProps = detailLink ? { to: detailLink } : {}
```

With:
```typescript
  const detailLink = `/announcements/${announcement.id}`
```

And change the `TitleTag` / `titleProps` pattern to always use `Link`:
```tsx
<Link
  to={detailLink}
  className="text-sm text-zinc-300 truncate block hover:text-white transition-colors"
>
  {announcement.h4_title}
</Link>
```

**Step 2: Update ReleaseDetail AnnouncementCard**

In `frontend/src/pages/ReleaseDetail.tsx`, update the `AnnouncementCard` component (lines 150-187). Make the h3 title a link to `/announcements/:id`:

Replace the plain `<h3>`:
```tsx
<h3 className="text-sm font-medium text-zinc-200">{announcement.h4_title}</h3>
```

With:
```tsx
<Link
  to={`/announcements/${announcement.id}`}
  className="text-sm font-medium text-zinc-200 hover:text-white transition-colors"
>
  {announcement.h4_title}
</Link>
```

Keep the existing "view option" / "view setting" links at the bottom of each card — they provide secondary navigation.

Add `Link` to the imports if not already imported (it is already imported in ReleaseDetail.tsx).

**Step 3: Verify in browser**

- On dashboard, click any announcement row → should navigate to `/announcements/:id`
- On release detail page, click any announcement title → should navigate to `/announcements/:id`
- Entries that previously weren't clickable (like "Availability and Exceptions") should now be clickable

**Step 4: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/ReleaseDetail.tsx
git commit -m "feat: link all announcement entries to /announcements/:id"
```

---

### Task 6: Update LLM prompt for 3-5 sentence descriptions

**Files:**
- Modify: `src/processor/content_processor.py` (two methods)

**Step 1: Update `summarize_feature` prompt**

In `src/processor/content_processor.py`, update `FEATURE_SUMMARIZATION_PROMPT` (line 242):

Replace:
```
Write a 2-3 sentence summary that covers:
1. What this feature does
2. Who benefits from it (students, instructors, admins)
3. The key improvement or capability it provides
```

With:
```
Write a 3-5 sentence summary that covers:
1. What this feature does or what changed
2. Who benefits from it (students, instructors, admins)
3. The key improvement or capability it provides
4. Any important configuration or rollout details
```

**Step 2: Update `DEPLOY_CHANGE_PROMPT`**

In the same file, update `DEPLOY_CHANGE_PROMPT` (line 257):

Replace:
```
Write a 2-3 sentence summary that covers:
1. What behavior changed
2. Why it was changed (bug fix, improvement, accessibility, etc.)
3. Who needs to be aware of this change
```

With:
```
Write a 3-5 sentence summary that covers:
1. What behavior changed
2. Why it was changed (bug fix, improvement, accessibility, etc.)
3. Who needs to be aware of this change
4. Any action items or things to watch for
```

**Step 3: Update `summarize_announcement_description`**

Update the `summarize_announcement_description` method (line 918). Change the prompt:

Replace:
```python
prompt = f"""Summarize this Canvas release note entry in 1-2 sentences. What changed or was added?

Title: {h4_title}
Content: {raw_content[:2000]}"""
```

With:
```python
prompt = f"""Summarize this Canvas release note entry in 3-5 sentences for educational technologists. Cover what changed or was added, why it matters, and who it affects.

Title: {h4_title}
Content: {raw_content[:2000]}"""
```

**Step 4: Commit**

```bash
git add src/processor/content_processor.py
git commit -m "feat: update LLM prompts for 3-5 sentence descriptions"
```

---

### Task 7: Create and run announcement description regeneration script

**Files:**
- Create: `src/backfill_announcement_descriptions.py`

**Step 1: Create the backfill script**

Create `src/backfill_announcement_descriptions.py` following the pattern of the existing `src/backfill_descriptions.py`:

```python
#!/usr/bin/env python3
"""Regenerate announcement descriptions with longer 3-5 sentence format.

Usage:
    python src/backfill_announcement_descriptions.py
    python src/backfill_announcement_descriptions.py --dry-run
"""

import sys
import argparse
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))

from utils.database import Database
from processor.content_processor import ContentProcessor


def backfill_announcement_descriptions(dry_run: bool = False):
    db = Database()
    processor = ContentProcessor()
    conn = db._get_connection()
    cursor = conn.cursor()

    # Get all announcements with their raw content
    cursor.execute("""
        SELECT fa.id, fa.h4_title, fa.description,
               fa.content_id, ci.url
        FROM feature_announcements fa
        JOIN content_items ci ON fa.content_id = ci.source_id
        ORDER BY fa.id
    """)
    announcements = [dict(row) for row in cursor.fetchall()]

    print(f"Found {len(announcements)} announcements to regenerate")

    count = 0
    for ann in announcements:
        try:
            # Use h4_title as context since raw_content may not be stored
            new_desc = processor.summarize_announcement_description(
                ann["h4_title"],
                ann["description"] or ann["h4_title"]
            )
            if new_desc:
                if not dry_run:
                    cursor.execute(
                        "UPDATE feature_announcements SET description = ? WHERE id = ?",
                        (new_desc, ann["id"])
                    )
                    conn.commit()
                count += 1
                print(f"  [{count}] {ann['h4_title']}: {new_desc[:80]}...")
            else:
                print(f"  [empty] {ann['h4_title']}")
        except Exception as e:
            print(f"  [error] {ann['h4_title']}: {e}")

    print(f"\nRegenerated {count}/{len(announcements)} descriptions")
    if dry_run:
        print("(dry run - no DB changes made)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    backfill_announcement_descriptions(dry_run=args.dry_run)
```

**Step 2: Run dry-run first**

```bash
python src/backfill_announcement_descriptions.py --dry-run
```

Expected: Prints generated descriptions without writing to DB.

**Step 3: Run for real**

```bash
python src/backfill_announcement_descriptions.py
```

Expected: Updates all announcement descriptions in the database.

**Step 4: Commit**

```bash
git add src/backfill_announcement_descriptions.py
git commit -m "feat: add announcement description regeneration script"
```

---

### Task 8: Remove description truncation from Dashboard

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

**Step 1: Remove truncation from description in AnnouncementRow**

In `frontend/src/pages/Dashboard.tsx`, in the `AnnouncementRow` component, find the description paragraph (around line 303):

Replace:
```tsx
<p className="text-xs text-zinc-500 truncate mt-0.5">{announcement.description}</p>
```

With:
```tsx
<p className="text-xs text-zinc-500 mt-0.5 line-clamp-2">{announcement.description}</p>
```

This changes from single-line truncation to allowing 2 lines with CSS line clamping, which shows more content while still keeping the dashboard compact.

**Step 2: Verify in browser**

Check that dashboard announcement descriptions now show 2 lines instead of being truncated to 1.

**Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "fix: show 2-line descriptions on dashboard instead of truncated single line"
```

---

### Task 9: Final verification

**Step 1: Verify all four issues are resolved**

1. "View Online" text appears in Dashboard and ReleaseDetail (not "View on Canvas")
2. All announcement entries are clickable on both Dashboard and ReleaseDetail
3. Clicking any entry goes to `/announcements/:id` (not directly to option/setting)
4. Descriptions are 3-5 sentences; dashboard shows 2 lines, detail page shows full text

**Step 2: Spot-check edge cases**

- Click an entry that has no option/setting (like "Availability and Exceptions") → should still link to announcement detail
- Click an entry that has an option → announcement detail should show "Related Feature" section
- Verify back-link from announcement detail goes to correct parent release

**Step 3: Final commit if any cleanup needed**
