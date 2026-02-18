# Canonical Feature Descriptions

**Date:** 2026-02-17
**Status:** Approved

## Goal

Generate stable, glossary-style descriptions for every canonical feature, feature option, and feature setting. Display these as a "Description" heading in the feature registry and detail pages.

## What Changes

### Backfill Script: `src/backfill_descriptions.py`

A one-time script that:

1. Clears existing `description` values in `features`, `feature_options`, and `feature_settings` tables
2. For each feature in `CANVAS_FEATURES` (constants.py), calls Gemini with just the feature name to generate a 2-3 sentence canonical description
3. For each feature option in DB, calls Gemini with `canonical_name` + parent feature name
4. For each feature setting in DB, calls Gemini with setting `name` + parent feature name
5. Updates `llm_generated_at` timestamps

Prompt style: "Describe the {name} in Canvas LMS in 2-3 sentences. What is it and what does it let users do? Write for educational technologists."

Uses Gemini's built-in Canvas LMS knowledge (no scraped content needed).

### Frontend Changes

**FeatureAccordion (Registry):** Show feature description between header and options/settings lists when expanded, under a "Description" heading.

**FeatureDetail page:** Show description under a "Description" heading section.

**OptionDetail page:** Show `description` under a "Description" heading. Keep `meta_summary` visible separately under a "Deployment Readiness" heading.

**SettingDetail page:** Same as OptionDetail - "Description" heading + separate "Deployment Readiness" for meta_summary.

### What's NOT Touched

- `feature_announcements.description` - per-announcement summaries, different purpose
- `feature_options.meta_summary` - kept visible separately as "Deployment Readiness"
- `feature_settings.meta_summary` - kept visible separately as "Deployment Readiness"

## Database

No schema changes. Reuses existing `description` columns on `features`, `feature_options`, and `feature_settings` tables.
