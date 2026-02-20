# Dashboard Announcement Row Restructure

**Date:** 2026-02-20
**Status:** Approved

## Goal

Restructure dashboard Release Notes and Deploy Notes rows to lead with the tool category (e.g. "Canvas Apps", "New Quizzes", "Assignments") instead of the status pill, matching the layout style of the release detail page.

## Current Layout

```
[SETTING]  Title text here...              Beta Jan 19  Prod Feb 21
           Description text...
```

Status pill is the left-side prefix. No category information visible.

## New Layout

```
[Canvas Apps]  Title text here...
               Description text...
               Beta Jan 19  Prod Feb 21  [SETTING]
```

Category pill becomes the left-side prefix. Status pill moves to a bottom row alongside dates.

## Changes

### 1. AnnouncementRow component (`Dashboard.tsx`, lines 274-306)

- **Left column:** Replace `StatusPill` with a category pill showing `announcement.category || 'General'`
- **Width:** Widen from `w-20` to `w-28` to accommodate longer category names
- **Category pill styling:** `pill bg-surface-3 text-zinc-500` (matching release detail page)
- **Right area:** Move date pills and status pill into a bottom row beneath the description
- **Status pill placement:** After date pills in the bottom row, right-aligned or inline

### 2. No API changes needed

The `category` field is already returned in the dashboard API response (`dashboard.py` line 24).

### 3. Scope

Applies to both Release Notes and Deploy Notes sections (both use `AnnouncementRow`).

### 4. Fallback

When `category` is null or empty, display "General" as the fallback text.
