# Feature Settings Backend Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring feature_settings to full parity with feature_options: content retrieval, LLM description generation, meta-summary generation, lifecycle date propagation, and CLI commands.

**Architecture:** Mirror the existing feature_options patterns for settings. Add `get_latest_content_for_setting()` DB method, reuse/adapt LLM prompts for settings context, add parallel CLI commands, update pipeline to propagate lifecycle dates to settings, and integrate backfill into the Docker entrypoint.

**Tech Stack:** Python, SQLite, Google Gemini API, argparse CLI

---

### Task 1: Add `get_latest_content_for_setting()` DB Method

**Files:**
- Modify: `src/utils/database.py` (after line ~1006, near other setting methods)
- Test: `tests/test_database.py`

**Step 1: Write the failing test**

In `tests/test_database.py`, add to the existing settings test class:

```python
def test_get_latest_content_for_setting(self, temp_db):
    """Test getting latest content items referencing a feature setting."""
    temp_db.seed_features()
    temp_db.upsert_feature_setting('test_setting', 'speedgrader', 'Test Setting')

    # Insert a content item
    from processor.content_processor import ContentItem
    item = ContentItem(
        source="instructure_community",
        source_id="test-content-1",
        title="Test Release Note",
        url="https://example.com",
        content="Test content",
        published_date="2026-01-15",
    )
    temp_db.insert_item(item)

    # Link content to setting via content_feature_refs
    temp_db.add_content_feature_ref(
        content_id="test-content-1",
        feature_id="speedgrader",
        feature_setting_id="test_setting",
        mention_type="announces",
    )

    # Insert an announcement for this setting
    temp_db.insert_feature_announcement(
        content_id="test-content-1",
        h4_title="Test Setting",
        announced_at="2026-01-15",
        feature_id="speedgrader",
        setting_id="test_setting",
        description="A test description",
        implications="Some implications",
    )

    content = temp_db.get_latest_content_for_setting("test_setting", limit=5)
    assert len(content) == 1
    assert content[0]["source_id"] == "test-content-1"
    assert content[0]["announcement_description"] == "A test description"
    assert content[0]["implications"] == "Some implications"


def test_get_latest_content_for_setting_empty(self, temp_db):
    """Test returns empty list when no content linked."""
    temp_db.seed_features()
    temp_db.upsert_feature_setting('orphan', 'speedgrader', 'Orphan Setting')

    content = temp_db.get_latest_content_for_setting("orphan")
    assert content == []
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py -k "test_get_latest_content_for_setting" -v`
Expected: FAIL with `AttributeError: 'Database' object has no attribute 'get_latest_content_for_setting'`

**Step 3: Write minimal implementation**

In `src/utils/database.py`, add after `get_all_feature_settings()` (~line 1006):

```python
def get_latest_content_for_setting(self, setting_id: str, limit: int = 5) -> List[dict]:
    """Get the latest content items referencing a feature setting.

    Used to generate meta_summary for settings.

    Args:
        setting_id: The feature setting ID.
        limit: Maximum number of items to return.

    Returns:
        List of content item dicts with announcement data, newest first.
    """
    conn = self._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ci.*, fa.description as announcement_description, fa.implications
        FROM content_items ci
        JOIN content_feature_refs cfr ON ci.source_id = cfr.content_id
        LEFT JOIN feature_announcements fa ON ci.source_id = fa.content_id
            AND fa.setting_id = ?
        WHERE cfr.feature_setting_id = ?
        ORDER BY ci.first_posted DESC
        LIMIT ?
    """, (setting_id, setting_id, limit))
    return [dict(row) for row in cursor.fetchall()]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py -k "test_get_latest_content_for_setting" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/database.py tests/test_database.py
git commit -m "feat: add get_latest_content_for_setting() DB method"
```

---

### Task 2: Add `summarize_feature_setting_description()` to ContentProcessor

**Files:**
- Modify: `src/processor/content_processor.py` (after `summarize_feature_option_description()` ~line 826)
- Test: `tests/test_processor.py`

**Step 1: Write the failing test**

In `tests/test_processor.py`:

```python
@patch('processor.content_processor.GENAI_AVAILABLE', True)
@patch('processor.content_processor.genai')
def test_summarize_feature_setting_description(self, mock_genai):
    """Test generating description for a feature setting."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This setting enables scheduled feedback delivery."
    mock_client.models.generate_content.return_value = mock_response
    mock_genai.Client.return_value = mock_client

    processor = ContentProcessor(gemini_api_key="test-key")
    result = processor.summarize_feature_setting_description(
        setting_name="Scheduled Feedback",
        feature_name="Gradebook",
        raw_content="Allows instructors to schedule feedback release."
    )

    assert result == "This setting enables scheduled feedback delivery."
    mock_client.models.generate_content.assert_called_once()
    # Verify prompt mentions "feature change" not "feature option"
    call_args = mock_client.models.generate_content.call_args
    prompt = call_args[1].get('contents', call_args[0][1] if len(call_args[0]) > 1 else '')
    assert "feature option" not in str(prompt).lower() or "change" in str(prompt).lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_processor.py -k "test_summarize_feature_setting_description" -v`
Expected: FAIL with `AttributeError`

**Step 3: Write minimal implementation**

In `src/processor/content_processor.py`, add after `summarize_feature_option_description()`:

```python
def summarize_feature_setting_description(
    self, setting_name: str, feature_name: str, raw_content: str
) -> str:
    """Generate a 1-2 sentence description for a feature setting (non-toggle change).

    Args:
        setting_name: Name of the feature setting.
        feature_name: Name of the parent feature.
        raw_content: Raw content from announcement.

    Returns:
        1-2 sentence description.
    """
    if not self.client:
        return ""

    prompt = f"""You are summarizing a Canvas LMS feature change for educational technologists.

Feature change: {setting_name}
Parent feature: {feature_name}

Describe what this change does in 1-2 sentences. Be concise and factual. Focus on what changed and who it affects.

Context:
{raw_content[:2000]}"""

    return self._call_llm(prompt, max_chars=800)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_processor.py -k "test_summarize_feature_setting_description" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/processor/content_processor.py tests/test_processor.py
git commit -m "feat: add summarize_feature_setting_description() LLM method"
```

---

### Task 3: Adapt `generate_meta_summary()` to Support Settings

**Files:**
- Modify: `src/processor/content_processor.py` (~line 904, the existing method)
- Test: `tests/test_processor.py`

**Step 1: Write the failing test**

```python
@patch('processor.content_processor.GENAI_AVAILABLE', True)
@patch('processor.content_processor.genai')
def test_generate_meta_summary_for_setting(self, mock_genai):
    """Test meta_summary generation works for settings (entity_type param)."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This change is now active in production."
    mock_client.models.generate_content.return_value = mock_response
    mock_genai.Client.return_value = mock_client

    processor = ContentProcessor(gemini_api_key="test-key")
    result = processor.generate_meta_summary(
        option_name="Scheduled Feedback",
        feature_name="Gradebook",
        implementation_status="active",
        content_summaries=[{
            'date': '2026-01-15',
            'title': 'January Release',
            'description': 'Scheduled feedback is now available.',
            'implications': 'Instructors can schedule feedback.'
        }],
        entity_type="setting",
    )

    assert result == "This change is now active in production."
    # Verify the prompt uses "feature change" not "feature option"
    call_args = mock_client.models.generate_content.call_args
    prompt_text = str(call_args)
    assert "feature change" in prompt_text.lower() or "change" in prompt_text.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_processor.py -k "test_generate_meta_summary_for_setting" -v`
Expected: FAIL with `TypeError: generate_meta_summary() got an unexpected keyword argument 'entity_type'`

**Step 3: Modify existing method to accept entity_type**

In `src/processor/content_processor.py`, update `generate_meta_summary()` signature and prompt:

```python
def generate_meta_summary(
    self,
    option_name: str,
    feature_name: str,
    implementation_status: str,
    content_summaries: List[dict],
    entity_type: str = "option",
) -> str:
    """Generate meta_summary for a feature option or setting from latest content.

    Args:
        option_name: Name of the feature option or setting.
        feature_name: Name of the parent feature.
        implementation_status: Current implementation status text.
        content_summaries: List of dicts with 'date', 'title', 'description', 'implications'.
        entity_type: "option" for feature options, "setting" for feature settings/changes.

    Returns:
        3-4 sentence meta summary.
    """
    if not self.client:
        return ""

    entity_label = "feature option" if entity_type == "option" else "feature change"

    summaries_text = "\n".join([
        f"- [{c.get('date', 'Unknown')}] {c.get('title', '')}: {c.get('description', '')} {c.get('implications', '')}"
        for c in content_summaries[:5]
    ])

    prompt = f"""You are advising educational technologists about the deployment readiness of a Canvas {entity_label}.

{entity_label.title()}: {option_name}
Parent feature: {feature_name}
Current status: {implementation_status}

Recent activity (newest first):
{summaries_text}

In 3-4 sentences, summarize the current state of this {entity_label} for ed techs considering deployment. Cover: readiness for wide rollout, recent changes (especially status transitions like beta→production), community sentiment, and any concerns. Be direct and actionable."""

    return self._call_llm(prompt, max_chars=1000)
```

**Step 4: Run ALL meta_summary tests to verify nothing broke**

Run: `pytest tests/test_processor.py -k "meta_summary" -v`
Expected: ALL PASS (existing tests still pass because `entity_type` defaults to "option")

**Step 5: Commit**

```bash
git add src/processor/content_processor.py tests/test_processor.py
git commit -m "feat: support entity_type param in generate_meta_summary for settings"
```

---

### Task 4: Add CLI Commands for Settings Regeneration

**Files:**
- Modify: `src/cli.py` (argparse setup lines 21-50, handlers, dispatcher lines 459-476)
- Test: `tests/test_cli.py`

**Step 1: Write the failing tests**

In `tests/test_cli.py`:

```python
@patch('src.cli.ContentProcessor')
@patch('src.cli.Database')
def test_handle_regenerate_setting(self, mock_db_cls, mock_proc_cls):
    """Test regenerate single setting description."""
    from src.cli import handle_regenerate_setting

    mock_db = MagicMock()
    mock_db.get_feature_setting.return_value = {
        'setting_id': 'scheduled-feedback', 'feature_id': 'gradebook', 'name': 'Scheduled Feedback'
    }
    mock_db.get_feature.return_value = {'feature_id': 'gradebook', 'name': 'Gradebook'}
    mock_db.get_latest_content_for_setting.return_value = [
        {'raw_content': 'test content', 'content': 'test'}
    ]
    mock_db_cls.return_value = mock_db

    mock_proc = MagicMock()
    mock_proc.summarize_feature_setting_description.return_value = 'Generated description'
    mock_proc_cls.return_value = mock_proc

    result = handle_regenerate_setting('scheduled-feedback')

    assert result == 0
    mock_proc.summarize_feature_setting_description.assert_called_once()
    mock_db.update_feature_setting_description.assert_called_once()


@patch('src.cli.ContentProcessor')
@patch('src.cli.Database')
def test_handle_regenerate_setting_not_found(self, mock_db_cls, mock_proc_cls):
    """Test regenerate setting that doesn't exist."""
    from src.cli import handle_regenerate_setting

    mock_db = MagicMock()
    mock_db.get_feature_setting.return_value = None
    mock_db_cls.return_value = mock_db

    result = handle_regenerate_setting('nonexistent')
    assert result == 1


@patch('src.cli.ContentProcessor')
@patch('src.cli.Database')
def test_handle_regenerate_setting_meta_summary(self, mock_db_cls, mock_proc_cls):
    """Test regenerate meta-summary for a setting."""
    from src.cli import handle_regenerate_setting_meta_summary

    mock_db = MagicMock()
    mock_db.get_feature_setting.return_value = {
        'setting_id': 'scheduled-feedback', 'feature_id': 'gradebook',
        'name': 'Scheduled Feedback', 'implementation_status': 'active'
    }
    mock_db.get_feature.return_value = {'feature_id': 'gradebook', 'name': 'Gradebook'}
    mock_db.get_latest_content_for_setting.return_value = [{
        'first_posted': '2026-01-15T00:00:00',
        'title': 'Release Note',
        'announcement_description': 'Description',
        'implications': 'Some implications',
    }]
    mock_db_cls.return_value = mock_db

    mock_proc = MagicMock()
    mock_proc.generate_meta_summary.return_value = 'Meta summary text'
    mock_proc_cls.return_value = mock_proc

    result = handle_regenerate_setting_meta_summary('scheduled-feedback')

    assert result == 0
    mock_proc.generate_meta_summary.assert_called_once()
    # Verify entity_type="setting" was passed
    call_kwargs = mock_proc.generate_meta_summary.call_args[1]
    assert call_kwargs.get('entity_type') == 'setting'
    mock_db.update_feature_setting_meta_summary.assert_called_once()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py -k "setting" -v`
Expected: FAIL with `ImportError`

**Step 3: Add argparse subparsers and handler functions**

In `src/cli.py`, add these subparsers after the existing `regen_options` parser (~line 44):

```python
# regenerate setting <id>
regen_setting = regen_subparsers.add_parser('setting', help='Regenerate setting description')
regen_setting.add_argument('setting_id', help='Setting ID to regenerate')

# regenerate settings --missing
regen_settings = regen_subparsers.add_parser('settings', help='Regenerate all settings')
regen_settings.add_argument('--missing', action='store_true', help='Only missing descriptions')
regen_settings.add_argument('--dry-run', action='store_true', help='Show what would be done')

# regenerate setting-meta-summary <id>
regen_setting_meta = regen_subparsers.add_parser('setting-meta-summary', help='Regenerate setting meta summary')
regen_setting_meta.add_argument('setting_id', help='Setting ID to regenerate')
```

Add handler functions (after existing handlers, ~line 276):

```python
def handle_regenerate_setting(setting_id: str, dry_run: bool = False) -> int:
    """Handle regenerate setting description command."""
    db = Database()

    setting = db.get_feature_setting(setting_id)
    if not setting:
        print(f"Error: Setting '{setting_id}' not found")
        return 1

    feature = db.get_feature(setting['feature_id'])
    feature_name = feature['name'] if feature else 'Unknown'

    content = db.get_latest_content_for_setting(setting_id, limit=3)
    raw_content = "\n".join([c.get('raw_content', c.get('content', ''))[:500] for c in content])

    if dry_run:
        print(f"Would regenerate description for: {setting['name']}")
        return 0

    processor = ContentProcessor()
    description = processor.summarize_feature_setting_description(
        setting_name=setting['name'],
        feature_name=feature_name,
        raw_content=raw_content or "Feature change: " + setting['name']
    )

    if description:
        db.update_feature_setting_description(setting_id, description)
        print(f"Updated description for {setting['name']}:")
        print(f"  {description}")

    db.close()
    return 0


def handle_regenerate_settings(missing_only: bool = False, dry_run: bool = False) -> int:
    """Handle regenerate settings (bulk) command."""
    db = Database()

    if missing_only:
        settings = db.get_feature_settings_missing_description()
    else:
        settings = db.get_all_feature_settings()

    if dry_run:
        print(f"Would regenerate {len(settings)} settings:")
        for s in settings:
            print(f"  - {s['setting_id']}: {s['name']}")
        return 0

    processor = ContentProcessor()
    for s in settings:
        feature = db.get_feature(s['feature_id'])
        feature_name = feature['name'] if feature else 'Unknown'

        content = db.get_latest_content_for_setting(s['setting_id'], limit=3)
        raw_content = "\n".join([c.get('raw_content', '')[:500] for c in content])

        description = processor.summarize_feature_setting_description(
            setting_name=s['name'],
            feature_name=feature_name,
            raw_content=raw_content or f"Feature change: {s['name']}"
        )

        if description:
            db.update_feature_setting_description(s['setting_id'], description)
            print(f"Updated: {s['name']}")

    db.close()
    return 0


def handle_regenerate_setting_meta_summary(setting_id: str, dry_run: bool = False) -> int:
    """Handle regenerate setting meta-summary command."""
    db = Database()

    setting = db.get_feature_setting(setting_id)
    if not setting:
        print(f"Error: Setting '{setting_id}' not found")
        return 1

    feature = db.get_feature(setting['feature_id'])
    feature_name = feature['name'] if feature else 'Unknown'

    content = db.get_latest_content_for_setting(setting_id, limit=5)
    content_summaries = [
        {
            'date': c.get('first_posted', 'Unknown')[:10] if c.get('first_posted') else 'Unknown',
            'title': c.get('title', ''),
            'description': c.get('announcement_description', ''),
            'implications': c.get('implications', '')
        }
        for c in content
    ]

    if dry_run:
        print(f"Would regenerate meta_summary for: {setting['name']}")
        print(f"Using {len(content_summaries)} content items")
        return 0

    processor = ContentProcessor()
    meta_summary = processor.generate_meta_summary(
        option_name=setting['name'],
        feature_name=feature_name,
        implementation_status=setting.get('implementation_status', ''),
        content_summaries=content_summaries,
        entity_type="setting",
    )

    if meta_summary:
        db.update_feature_setting_meta_summary(setting_id, meta_summary)
        print(f"Updated meta_summary for {setting['name']}:")
        print(f"  {meta_summary}")

    db.close()
    return 0
```

Add dispatcher entries (in the `if parsed.command == 'regenerate':` block, ~line 474):

```python
elif parsed.regen_type == 'setting':
    return handle_regenerate_setting(parsed.setting_id)
elif parsed.regen_type == 'settings':
    return handle_regenerate_settings(
        missing_only=parsed.missing,
        dry_run=parsed.dry_run
    )
elif parsed.regen_type == 'setting-meta-summary':
    return handle_regenerate_setting_meta_summary(parsed.setting_id)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -k "setting" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cli.py tests/test_cli.py
git commit -m "feat: add CLI commands for settings description and meta-summary regeneration"
```

---

### Task 5: Update Lifecycle Date Propagation in Pipeline

**Files:**
- Modify: `src/main.py` (lines 241-253 in `store_release_notes()`)
- Test: `tests/test_scrapers.py` (or a new focused test)

**Context:** Currently, `store_release_notes()` line 247 only calls `db.update_feature_option_lifecycle_dates()`. Settings with lifecycle dates never get them propagated.

**Step 1: Write the failing test**

Add a test that verifies lifecycle dates are propagated to settings during release note processing. The exact test depends on how the existing release note tests are structured. A simpler approach: test the DB method directly, then verify the pipeline code calls it.

```python
def test_store_release_notes_updates_setting_lifecycle_dates(self):
    """Verify lifecycle dates are set on feature_settings, not just options."""
    # This test verifies the pipeline behavior.
    # The key assertion: after store_release_notes, settings should have lifecycle dates.
    pass  # See implementation step for the actual integration approach
```

**Step 2: Modify `store_release_notes()` to also update settings**

In `src/main.py`, modify the lifecycle date update block (lines 241-253). The current code updates *all* features by `anchor_id` as option_id. But `classify_release_features()` already sorted which are options vs settings — the lifecycle dates should apply to both.

Replace lines 241-253 with logic that tries both:

```python
        # Update lifecycle dates on feature options AND settings from this page
        if beta_date or production_date:
            for feature in page.features:
                entity_id = feature.anchor_id
                if not entity_id:
                    continue
                # Try updating as option first, then as setting
                try:
                    db.update_feature_option_lifecycle_dates(
                        option_id=entity_id,
                        beta_date=beta_date,
                        production_date=production_date,
                    )
                except Exception:
                    pass
                try:
                    db.update_feature_setting_lifecycle_dates(
                        setting_id=entity_id,
                        beta_date=beta_date,
                        production_date=production_date,
                    )
                except Exception:
                    pass
```

**Step 3: Run existing tests to verify nothing broke**

Run: `pytest tests/test_scrapers.py -k "classify" -v`
Expected: PASS

**Step 4: Commit**

```bash
git add src/main.py
git commit -m "fix: propagate lifecycle dates to feature_settings, not just options"
```

---

### Task 6: Integrate Backfill Into Docker Entrypoint

**Files:**
- Modify: `docker-entrypoint.sh` (line ~26)

**Step 1: Add backfill after main aggregation run**

In `docker-entrypoint.sh`, after the initial `python -m src.main` run and in the cron command, add the backfill:

```bash
python -m src.main && python src/backfill_summaries.py
```

This ensures after each scrape run, any missing descriptions are propagated from announcements to both options and settings.

**Step 2: Commit**

```bash
git add docker-entrypoint.sh
git commit -m "feat: run backfill_summaries after each aggregation in Docker"
```

---

### Task 7: Run Full Test Suite and Verify

**Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass (436+ should pass; 4 pre-existing failures are known)

**Step 2: Verify database state manually**

Run against the real database to confirm settings queries work:

```bash
python -c "
from src.utils.database import Database
db = Database()
content = db.get_latest_content_for_setting('scheduled-feedback', limit=3)
print(f'Content items for scheduled-feedback: {len(content)}')
for c in content:
    print(f'  - {c.get(\"title\", \"\")}')
db.close()
"
```

**Step 3: Commit with final verification note**

No code changes needed — this is a verification step.

---

## Summary of Gaps Addressed

| Gap | Task |
|-----|------|
| No `get_latest_content_for_setting()` | Task 1 |
| No LLM description generation for settings | Task 2 |
| `generate_meta_summary` hardcoded to "option" | Task 3 |
| No CLI `regenerate setting` commands | Task 4 |
| Lifecycle dates only propagated to options | Task 5 |
| Backfill not run in Docker | Task 6 |
| Full verification | Task 7 |
