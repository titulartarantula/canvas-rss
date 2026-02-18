# Canonical Descriptions Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate stable, glossary-style descriptions for every canonical feature, feature option, and feature setting via Gemini, then display them in the frontend under "Description" headings.

**Architecture:** One-time backfill script calls Gemini with just the entity name (no scraped content). Frontend shows the description in the registry accordion and detail pages. Meta-summary stays separate as "Deployment Readiness".

**Tech Stack:** Python (Gemini API via ContentProcessor), React/TypeScript frontend, SQLite.

---

### Task 1: Backfill Script — Generate Canonical Descriptions

**Files:**
- Create: `src/backfill_descriptions.py`
- Read: `src/constants.py` (CANVAS_FEATURES dict)
- Read: `src/processor/content_processor.py` (_call_llm method)
- Read: `src/utils/database.py` (update_feature_description, update_feature_option_description, update_feature_setting_description)

**Step 1: Add canonical description methods to ContentProcessor**

Modify: `src/processor/content_processor.py` — add two new methods after line 798.

```python
def generate_canonical_feature_description(self, feature_name: str) -> str:
    """Generate a stable, glossary-style description for a Canvas feature.

    Uses Gemini's built-in Canvas LMS knowledge (no scraped content needed).

    Args:
        feature_name: Display name of the Canvas feature (e.g., "Assignments").

    Returns:
        2-3 sentence canonical description.
    """
    if not self.client:
        return ""

    prompt = f"""You are writing a glossary entry for educational technologists at a university.

Describe the "{feature_name}" feature in Canvas LMS in 2-3 sentences. What is it and what does it let instructors, students, or admins do? Be concise and factual. Do not mention recent changes or updates."""

    return self._call_llm(prompt, max_chars=500)

def generate_canonical_option_description(self, option_name: str, feature_name: str) -> str:
    """Generate a stable, glossary-style description for a Canvas feature option.

    Uses Gemini's built-in Canvas LMS knowledge (no scraped content needed).

    Args:
        option_name: Canonical name of the feature option.
        feature_name: Display name of the parent feature.

    Returns:
        2-3 sentence canonical description.
    """
    if not self.client:
        return ""

    prompt = f"""You are writing a glossary entry for educational technologists at a university.

Describe the "{option_name}" feature option in Canvas LMS in 2-3 sentences. This option belongs to the {feature_name} feature area. What does enabling this option do? Who does it affect? Be concise and factual. Do not mention recent changes or release dates."""

    return self._call_llm(prompt, max_chars=500)

def generate_canonical_setting_description(self, setting_name: str, feature_name: str) -> str:
    """Generate a stable, glossary-style description for a Canvas feature setting/change.

    Uses Gemini's built-in Canvas LMS knowledge (no scraped content needed).

    Args:
        setting_name: Name of the feature setting.
        feature_name: Display name of the parent feature.

    Returns:
        2-3 sentence canonical description.
    """
    if not self.client:
        return ""

    prompt = f"""You are writing a glossary entry for educational technologists at a university.

Describe the "{setting_name}" change in the {feature_name} area of Canvas LMS in 2-3 sentences. What does this change do? Who does it affect? Be concise and factual. Do not mention specific release dates."""

    return self._call_llm(prompt, max_chars=500)
```

**Step 2: Create the backfill script**

Create: `src/backfill_descriptions.py`

```python
#!/usr/bin/env python3
"""Generate canonical (glossary-style) descriptions for features, options, and settings.

This is a one-time backfill script. It clears existing description values
and regenerates them using Gemini's built-in Canvas LMS knowledge.

Usage:
    python src/backfill_descriptions.py
    # Or dry-run (no DB writes):
    python src/backfill_descriptions.py --dry-run
"""

import os
import sys
import argparse
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))

from constants import CANVAS_FEATURES
from utils.database import Database
from processor.content_processor import ContentProcessor


def backfill_descriptions(dry_run: bool = False):
    db = Database()
    processor = ContentProcessor()
    conn = db._get_connection()
    cursor = conn.cursor()

    # Phase 1: Clear existing descriptions
    if not dry_run:
        print("Clearing existing descriptions...")
        cursor.execute("UPDATE features SET description = NULL, llm_generated_at = NULL")
        cursor.execute("UPDATE feature_options SET description = NULL, llm_generated_at = NULL")
        cursor.execute("UPDATE feature_settings SET description = NULL, llm_generated_at = NULL")
        conn.commit()
        print("  Cleared.")

    # Phase 2: Generate feature descriptions
    print(f"\n--- Features ({len(CANVAS_FEATURES)} total) ---")
    feature_count = 0
    for feature_id, feature_name in CANVAS_FEATURES.items():
        # Check feature exists in DB
        cursor.execute("SELECT feature_id FROM features WHERE feature_id = ?", (feature_id,))
        if not cursor.fetchone():
            print(f"  [skip] {feature_name}: not in DB")
            continue

        try:
            desc = processor.generate_canonical_feature_description(feature_name)
            if desc:
                if not dry_run:
                    db.update_feature_description(feature_id, desc)
                feature_count += 1
                print(f"  [{feature_count}] {feature_name}: {desc[:80]}...")
            else:
                print(f"  [empty] {feature_name}: LLM returned empty")
        except Exception as e:
            print(f"  [error] {feature_name}: {e}")

    print(f"\nGenerated {feature_count} feature descriptions.")

    # Phase 3: Generate feature option descriptions
    cursor.execute("""
        SELECT fo.option_id, fo.canonical_name, fo.name, f.name as feature_name
        FROM feature_options fo
        JOIN features f ON fo.feature_id = f.feature_id
        ORDER BY f.name, fo.name
    """)
    options = [dict(row) for row in cursor.fetchall()]

    print(f"\n--- Feature Options ({len(options)} total) ---")
    option_count = 0
    for opt in options:
        display_name = opt["canonical_name"] or opt["name"]
        feature_name = opt["feature_name"]

        try:
            desc = processor.generate_canonical_option_description(display_name, feature_name)
            if desc:
                if not dry_run:
                    db.update_feature_option_description(opt["option_id"], desc)
                option_count += 1
                print(f"  [{option_count}] {display_name}: {desc[:80]}...")
            else:
                print(f"  [empty] {display_name}: LLM returned empty")
        except Exception as e:
            print(f"  [error] {display_name}: {e}")

    print(f"\nGenerated {option_count} option descriptions.")

    # Phase 4: Generate feature setting descriptions
    cursor.execute("""
        SELECT fs.setting_id, fs.name, f.name as feature_name
        FROM feature_settings fs
        JOIN features f ON fs.feature_id = f.feature_id
        ORDER BY f.name, fs.name
    """)
    settings = [dict(row) for row in cursor.fetchall()]

    print(f"\n--- Feature Settings ({len(settings)} total) ---")
    setting_count = 0
    for setting in settings:
        setting_name = setting["name"]
        feature_name = setting["feature_name"]

        try:
            desc = processor.generate_canonical_setting_description(setting_name, feature_name)
            if desc:
                if not dry_run:
                    db.update_feature_setting_description(setting["setting_id"], desc)
                setting_count += 1
                print(f"  [{setting_count}/{len(settings)}] {setting_name}: {desc[:80]}...")
            else:
                print(f"  [empty] {setting_name}: LLM returned empty")
        except Exception as e:
            print(f"  [error] {setting_name}: {e}")

    print(f"\nGenerated {setting_count} setting descriptions.")
    print(f"\n=== Summary ===")
    print(f"Features: {feature_count}")
    print(f"Options:  {option_count}")
    print(f"Settings: {setting_count}")
    if dry_run:
        print("(dry run — no DB changes made)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate canonical descriptions")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    args = parser.parse_args()
    backfill_descriptions(dry_run=args.dry_run)
```

**Step 3: Commit**

```bash
git add src/backfill_descriptions.py src/processor/content_processor.py
git commit -m "feat: add canonical description generation script and LLM methods"
```

---

### Task 2: Frontend — Show Description in Feature Accordion (Registry)

**Files:**
- Modify: `frontend/src/components/FeatureAccordion.tsx:97-120` (FeatureAccordionContent)

**Step 1: Add feature description to accordion content**

In `FeatureAccordionContent`, between the loading check and the options/settings sections, add a description block. The `data` object already has `description` from the `/api/features/{id}` endpoint.

Replace the existing content div (lines 122-210) so the description appears first:

```tsx
// Inside FeatureAccordionContent, after the loading check, replace the return:
return (
    <div className="px-4 pb-4 pl-8 animate-fade-in">
      {/* Description */}
      {data?.description && (
        <div className="mb-4">
          <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 mb-1.5">
            Description
          </h3>
          <p className="text-sm text-zinc-400 leading-relaxed max-w-2xl">
            {data.description}
          </p>
        </div>
      )}

      {/* Options section - unchanged */}
      ...existing options code...

      {/* Settings section - unchanged */}
      ...existing settings code...

      {/* View full detail link - unchanged */}
      ...existing link code...
    </div>
  )
```

Specifically, insert this block after line 123 (`<div className="px-4 pb-4 pl-8 animate-fade-in">`) and before line 124 (`{/* Options section */}`):

```tsx
      {/* Description */}
      {data?.description && (
        <div className="mb-4">
          <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 mb-1.5">
            Description
          </h3>
          <p className="text-sm text-zinc-400 leading-relaxed max-w-2xl">
            {data.description}
          </p>
        </div>
      )}
```

**Step 2: Commit**

```bash
git add frontend/src/components/FeatureAccordion.tsx
git commit -m "feat: show feature description in registry accordion"
```

---

### Task 3: Frontend — Show Description on FeatureDetail Page

**Files:**
- Modify: `frontend/src/pages/FeatureDetail.tsx:82-86`

**Step 1: Replace plain description with headed section**

Currently lines 82-86:
```tsx
{data.description && (
  <p className="mt-3 text-sm text-zinc-400 leading-relaxed max-w-3xl">
    {data.description}
  </p>
)}
```

Replace with:
```tsx
{data.description && (
  <div className="mt-4">
    <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 mb-1.5">
      Description
    </h3>
    <p className="text-sm text-zinc-400 leading-relaxed max-w-3xl">
      {data.description}
    </p>
  </div>
)}
```

**Step 2: Commit**

```bash
git add frontend/src/pages/FeatureDetail.tsx
git commit -m "feat: add Description heading on feature detail page"
```

---

### Task 4: Frontend — Restructure OptionDetail Page Descriptions

**Files:**
- Modify: `frontend/src/pages/OptionDetail.tsx:81-90`

**Step 1: Replace current description display with headed sections**

Currently lines 81-90 show meta_summary as primary and description as secondary, both unlabeled. Replace with two labeled sections.

Replace:
```tsx
{data.meta_summary && (
  <p className="mt-3 text-sm text-zinc-400 leading-relaxed max-w-3xl">
    {data.meta_summary}
  </p>
)}
{data.description && data.description !== data.meta_summary && (
  <p className="mt-2 text-xs text-zinc-500 leading-relaxed max-w-3xl">
    {data.description}
  </p>
)}
```

With:
```tsx
{data.description && (
  <div className="mt-4">
    <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 mb-1.5">
      Description
    </h3>
    <p className="text-sm text-zinc-400 leading-relaxed max-w-3xl">
      {data.description}
    </p>
  </div>
)}
{data.meta_summary && (
  <div className="mt-4">
    <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 mb-1.5">
      Deployment Readiness
    </h3>
    <p className="text-sm text-zinc-400 leading-relaxed max-w-3xl">
      {data.meta_summary}
    </p>
  </div>
)}
```

**Step 2: Commit**

```bash
git add frontend/src/pages/OptionDetail.tsx
git commit -m "feat: add Description and Deployment Readiness headings on option detail"
```

---

### Task 5: Frontend — Restructure SettingDetail Page Descriptions

**Files:**
- Modify: `frontend/src/pages/SettingDetail.tsx:95-104`

**Step 1: Replace current description display with headed sections**

Same pattern as OptionDetail. Replace lines 95-104:

```tsx
{data.meta_summary && (
  <p className="mt-3 text-sm text-zinc-400 leading-relaxed max-w-3xl">
    {data.meta_summary}
  </p>
)}
{data.description && data.description !== data.meta_summary && (
  <p className="mt-2 text-xs text-zinc-500 leading-relaxed max-w-3xl">
    {data.description}
  </p>
)}
```

With:
```tsx
{data.description && (
  <div className="mt-4">
    <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 mb-1.5">
      Description
    </h3>
    <p className="text-sm text-zinc-400 leading-relaxed max-w-3xl">
      {data.description}
    </p>
  </div>
)}
{data.meta_summary && (
  <div className="mt-4">
    <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 mb-1.5">
      Deployment Readiness
    </h3>
    <p className="text-sm text-zinc-400 leading-relaxed max-w-3xl">
      {data.meta_summary}
    </p>
  </div>
)}
```

**Step 2: Commit**

```bash
git add frontend/src/pages/SettingDetail.tsx
git commit -m "feat: add Description and Deployment Readiness headings on setting detail"
```

---

### Task 6: Run the Backfill

**Step 1: Dry-run first**

```bash
cd /c/Users/mclea/claude/canvas-rss
python src/backfill_descriptions.py --dry-run
```

Expected: See generated descriptions printed for each feature, option, and setting without DB changes.

**Step 2: Run for real**

```bash
python src/backfill_descriptions.py
```

Expected: Descriptions stored in DB. Output shows counts matching total features/options/settings.

**Step 3: Verify via API**

```bash
# Kill any existing server
powershell -Command "Get-NetTCPConnection -State Listen -LocalPort 8986 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"

# Start server
cd /c/Users/mclea/claude/canvas-rss && python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8986 &

# Check a feature has description
curl -s http://localhost:8986/api/features/assignments | python -m json.tool | head -10
```

Expected: The `description` field contains a canonical glossary-style description.

**Step 4: Visual check via browser**

Navigate to `http://localhost:8986/registry`, expand a feature accordion, and verify the "Description" heading appears with text.

Navigate to a feature detail, option detail, and setting detail page to verify headings.

---

### Task 7: Commit and Verify

**Step 1: Run existing tests**

```bash
pytest tests/ -v --timeout=30
```

Expected: All existing tests pass (no schema changes, so no breakage expected).

**Step 2: Final commit if needed**

Only if any fixes were needed during verification.
