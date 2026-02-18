# Canvas RSS CLI Reference

Command-line interface for managing canvas-rss features, options, and LLM-generated summaries.

## Usage

```bash
python -m src.cli <command> [options]
```

## Commands

### regenerate

Regenerate LLM-generated summaries for features and feature options.

#### regenerate feature \<id\>

Regenerate the description for a single Canvas feature.

```bash
python -m src.cli regenerate feature speedgrader
python -m src.cli regenerate feature assignments
```

#### regenerate option \<id\>

Regenerate the description for a single feature option.

```bash
python -m src.cli regenerate option document_processor
python -m src.cli regenerate option performance_upgrades
```

#### regenerate meta-summary \<id\>

Regenerate the meta_summary for a feature option based on recent content.

```bash
python -m src.cli regenerate meta-summary document_processor
```

#### regenerate features

Regenerate descriptions for multiple features.

```bash
# Regenerate all features
python -m src.cli regenerate features

# Only regenerate features missing descriptions
python -m src.cli regenerate features --missing

# Preview what would be regenerated
python -m src.cli regenerate features --missing --dry-run
```

Options:
- `--missing` - Only process features without descriptions
- `--dry-run` - Show what would be done without making changes

#### regenerate options

Regenerate descriptions for multiple feature options.

```bash
# Regenerate all options
python -m src.cli regenerate options

# Only regenerate options missing descriptions
python -m src.cli regenerate options --missing

# Preview
python -m src.cli regenerate options --missing --dry-run
```

Options:
- `--missing` - Only process options without descriptions
- `--dry-run` - Show what would be done without making changes

#### regenerate meta-summaries

Regenerate meta_summaries for all feature options.

```bash
python -m src.cli regenerate meta-summaries --all
python -m src.cli regenerate meta-summaries --all --dry-run
```

Options:
- `--all` - Regenerate all meta_summaries
- `--dry-run` - Show what would be done without making changes

---

### general

Manage content tagged with the 'general' feature (content that couldn't be auto-matched to a specific feature).

#### general list

List all content items tagged as 'general'.

```bash
python -m src.cli general list
```

Output shows content ID, date, and title for each item.

#### general show \<id\>

Show details of a specific content item.

```bash
python -m src.cli general show blog_12345
```

#### general assign \<id\>

Assign a content item to a feature or option.

```bash
# Assign to existing feature
python -m src.cli general assign blog_12345 --feature speedgrader

# Assign to existing option
python -m src.cli general assign blog_12345 --option document_processor

# Create new feature and assign
python -m src.cli general assign blog_12345 --new-feature new_feature_id "New Feature Name"

# Create new option and assign
python -m src.cli general assign blog_12345 --new-option speedgrader new_option_id "New Option Name"
```

Options:
- `--feature <id>` - Assign to existing feature
- `--option <id>` - Assign to existing option
- `--new-feature <id> <name>` - Create new feature and assign
- `--new-option <feature_id> <option_id> <name>` - Create new option and assign

#### general triage

Interactive triage of 'general'-tagged content with suggested matches.

```bash
# Interactive mode
python -m src.cli general triage

# Auto-assign items with 80%+ confidence
python -m src.cli general triage --auto-high

# Filter to last 7 days
python -m src.cli general triage --days 7

# Export suggestions to CSV
python -m src.cli general triage --export triage_suggestions.csv
```

Options:
- `--auto-high` - Automatically assign items with ≥80% confidence match
- `--days <n>` - Only show items from the last N days
- `--export <file>` - Export suggestions to CSV instead of interactive mode

In interactive mode, the CLI shows:
1. Content preview (title, date, snippet)
2. Top 3 suggested feature matches with confidence scores
3. Options to select a suggestion, skip, create new, or quit

---

## Exit Codes

- `0` - Success
- `1` - Error (invalid command, item not found, etc.)

## Examples

### Initial Setup After Database Rebuild

```bash
# Generate descriptions for all features
python -m src.cli regenerate features

# Generate descriptions for all options
python -m src.cli regenerate options --missing
```

### Daily Maintenance

```bash
# Check for unclassified content
python -m src.cli general list

# Triage recent items
python -m src.cli general triage --days 7

# Auto-assign high confidence matches
python -m src.cli general triage --auto-high --days 7
```

### Regenerating After Content Updates

```bash
# Regenerate meta_summary for a specific option after new announcements
python -m src.cli regenerate meta-summary document_processor
```
