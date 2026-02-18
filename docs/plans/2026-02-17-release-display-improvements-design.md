# Release & Deploy Notes Display Improvements

**Date:** 2026-02-17
**Status:** Approved

## Problem

The dashboard and release detail pages have several display issues:

1. "View on Canvas" button text is misleading — not all links go to Canvas
2. Announcement entries without an `option_id` or `setting_id` are not clickable
3. Clickable entries link to feature option/setting pages instead of the announcement itself
4. Descriptions are 1-2 sentences, too short to be useful; detail pages also show truncated content

## Design

### 1. "View on Canvas" → "View Online"

Text change in two locations:
- `frontend/src/pages/Dashboard.tsx` — AnnouncementsTable external link
- `frontend/src/pages/ReleaseDetail.tsx` — header external link

### 2. New Announcement Detail Page

**Route:** `/announcements/:id` (where `id` is `feature_announcements.id`)

**Content:**
- h4_title as page heading
- Full 3-5 sentence description
- Section and category labels
- Beta and production dates
- "View Online" link to original Canvas page (constructed from parent `content_items.url` + `anchor_id`)
- Back-link to parent release note (`/releases/:contentId`)
- If `option_id` or `setting_id` exists: secondary "Related Feature" section with link to `/options/:optionId` or `/settings/:settingId`

**New API endpoint:** `GET /api/announcements/:id`

Returns announcement fields joined with:
- Parent release info (title, source_id, url) from `content_items`
- Option name from `feature_options` (if `option_id` set)
- Setting name from `feature_settings` (if `setting_id` set)

### 3. All Entries Link to Announcement Detail

Every announcement row across the app links to `/announcements/:id` as the primary target:
- Dashboard AnnouncementsTable rows
- ReleaseDetail AnnouncementCard titles

Option/setting detail pages remain accessible via the announcement detail page's "Related Feature" section.

### 4. Longer Descriptions (3-5 sentences)

**LLM prompt update:** Modify the description generation prompt to request 3-5 sentences covering what changed, why it matters, and who it affects.

**Regeneration:** One-time script to regenerate descriptions for all existing announcements.

**Display:** Full description shown everywhere — no truncation on dashboard or detail pages.

## Scope

- Frontend: 3 modified files (Dashboard.tsx, ReleaseDetail.tsx, App.tsx), 1 new page component
- Backend: 1 new API endpoint, LLM prompt modification
- Data: Description regeneration for existing records
