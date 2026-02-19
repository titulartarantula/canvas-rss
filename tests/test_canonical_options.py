"""Tests for the canonical feature options page parser."""

import pytest
from src.scrapers.canonical_options import (
    CanonicalOption,
    ConfigParseResult,
    parse_config_text,
    parse_canonical_page_html,
    _extract_config_text_from_cell,
    _resolve_redirect_url,
)


# ============================================================================
# Tests for parse_config_text
# ============================================================================


class TestParseConfigText:
    """Tests for the config text parser."""

    # --- Basic account-level formats ---

    def test_account_disabled_unlocked(self):
        result = parse_config_text("Account (Disabled/Unlocked)")
        assert result.prod_account_state == "disabled_unlocked"
        assert result.prod_course_state == "N/A"
        assert result.beta_account_state == "N/A"
        assert result.beta_course_state == "N/A"

    def test_account_disabled_locked(self):
        result = parse_config_text("Account (Disabled/Locked)")
        assert result.prod_account_state == "disabled_locked"
        assert result.prod_course_state == "N/A"

    def test_account_enabled_unlocked(self):
        result = parse_config_text("Account (Enabled/Unlocked)")
        assert result.prod_account_state == "enabled_unlocked"
        assert result.prod_course_state == "N/A"

    def test_account_enabled_locked(self):
        result = parse_config_text("Account (Enabled/Locked)")
        assert result.prod_account_state == "enabled_locked"
        assert result.prod_course_state == "N/A"

    def test_account_disabled_no_lock(self):
        """Account-only feature with no lock concept."""
        result = parse_config_text("Account (Disabled)")
        assert result.prod_account_state == "disabled"
        assert result.prod_course_state == "N/A"

    def test_account_enabled_no_lock(self):
        """Account-only feature with no lock concept, enabled."""
        result = parse_config_text("Account (Enabled)")
        assert result.prod_account_state == "enabled"
        assert result.prod_course_state == "N/A"

    # --- Account/Course combined ---

    def test_account_course_disabled_unlocked(self):
        """Account/Course feature - course gets no lock."""
        result = parse_config_text("Account/Course (Disabled/Unlocked)")
        assert result.prod_account_state == "disabled_unlocked"
        assert result.prod_course_state == "disabled"

    def test_account_course_enabled_unlocked(self):
        result = parse_config_text("Account/Course (Enabled/Unlocked)")
        assert result.prod_account_state == "enabled_unlocked"
        assert result.prod_course_state == "enabled"

    # --- Course-only ---

    def test_course_disabled(self):
        result = parse_config_text("Course (Disabled)")
        assert result.prod_account_state == "N/A"
        assert result.prod_course_state == "disabled"

    def test_course_enabled(self):
        result = parse_config_text("Course (Enabled)")
        assert result.prod_account_state == "N/A"
        assert result.prod_course_state == "enabled"

    # --- Special configurations ---

    def test_csm_managed(self):
        result = parse_config_text(
            "Must be configured by a Customer Success Manager (CSM)"
        )
        assert result.prod_account_state == "csm_managed"
        assert result.prod_course_state == "N/A"

    def test_lti_required(self):
        result = parse_config_text("LTI Configuration Required")
        assert result.prod_account_state == "lti_required"
        assert result.prod_course_state == "N/A"

    def test_user_settings_disabled(self):
        result = parse_config_text("User Settings (Disabled)")
        assert result.prod_account_state == "user_setting"
        assert result.prod_course_state == "N/A"

    def test_enabled_by_default(self):
        result = parse_config_text("Enabled by default")
        assert result.prod_account_state == "enabled_unlocked"
        assert result.prod_course_state == "N/A"

    # --- No level prefix ---

    def test_no_prefix_disabled_unlocked(self):
        """State with no level prefix - treated as account."""
        result = parse_config_text("(Disabled/Unlocked)")
        assert result.prod_account_state == "disabled_unlocked"
        assert result.prod_course_state == "N/A"

    # --- Multi-line (separate paragraphs in real HTML) ---

    def test_multiline_account_locked_course_disabled(self):
        """Account (Disabled/Locked) + Course (Disabled) as separate lines."""
        result = parse_config_text(
            "Account (Disabled/Locked)\nCourse (Disabled)"
        )
        assert result.prod_account_state == "disabled_locked"
        assert result.prod_course_state == "disabled"

    def test_multiline_account_unlocked_course_disabled(self):
        result = parse_config_text(
            "Account (Disabled/Unlocked)\nCourse (Disabled)"
        )
        assert result.prod_account_state == "disabled_unlocked"
        assert result.prod_course_state == "disabled"

    def test_semicolon_separated(self):
        """Semicolon separator instead of newline."""
        result = parse_config_text(
            "Account (Disabled/Locked); Course (Disabled)"
        )
        assert result.prod_account_state == "disabled_locked"
        assert result.prod_course_state == "disabled"

    # --- Typo/formatting: state on separate line from level ---

    def test_split_account_state(self):
        """Account and state split across lines (real typo on page)."""
        result = parse_config_text("Account\n(Disabled/Unlocked)")
        assert result.prod_account_state == "disabled_unlocked"
        assert result.prod_course_state == "N/A"

    # --- Beta/Production split ---

    def test_beta_prod_split(self):
        """Beta and Production on separate lines."""
        result = parse_config_text(
            "Beta: Account/Course (Enabled/Unlocked)\n"
            "Production: Account/Course (Disabled/Unlocked)"
        )
        assert result.beta_account_state == "enabled_unlocked"
        assert result.beta_course_state == "enabled"
        assert result.prod_account_state == "disabled_unlocked"
        assert result.prod_course_state == "disabled"

    def test_beta_prod_semicolon(self):
        """Beta/Production split with semicolons."""
        result = parse_config_text(
            "Beta: Account/Course (Enabled/Unlocked); "
            "Production: Account/Course (Disabled/Unlocked)"
        )
        assert result.beta_account_state == "enabled_unlocked"
        assert result.beta_course_state == "enabled"
        assert result.prod_account_state == "disabled_unlocked"
        assert result.prod_course_state == "disabled"

    def test_beta_only(self):
        """Only beta line present."""
        result = parse_config_text(
            "Beta: Account (Enabled/Unlocked)"
        )
        assert result.beta_account_state == "enabled_unlocked"
        assert result.prod_account_state == "N/A"

    def test_beta_account_only_prod_account_course(self):
        """Different levels in beta vs production."""
        result = parse_config_text(
            "Beta: Account (Enabled/Unlocked)\n"
            "Production: Account/Course (Disabled/Unlocked)"
        )
        assert result.beta_account_state == "enabled_unlocked"
        assert result.beta_course_state == "N/A"
        assert result.prod_account_state == "disabled_unlocked"
        assert result.prod_course_state == "disabled"

    # --- Edge cases ---

    def test_empty_string(self):
        result = parse_config_text("")
        assert result.prod_account_state == "N/A"
        assert result.prod_course_state == "N/A"
        assert result.beta_account_state == "N/A"
        assert result.beta_course_state == "N/A"

    def test_none_string(self):
        result = parse_config_text(None)
        assert result.prod_account_state == "N/A"

    def test_whitespace_only(self):
        result = parse_config_text("   \n  ")
        assert result.prod_account_state == "N/A"

    def test_trailing_whitespace(self):
        result = parse_config_text("  Account (Disabled/Unlocked)  ")
        assert result.prod_account_state == "disabled_unlocked"

    def test_multiline_with_empty_line(self):
        """Multi-line with a blank line (from &nbsp; in HTML)."""
        result = parse_config_text(
            "Account (Disabled/Unlocked)\n\nCourse (Disabled)"
        )
        assert result.prod_account_state == "disabled_unlocked"
        assert result.prod_course_state == "disabled"


# ============================================================================
# Tests for _resolve_redirect_url
# ============================================================================


class TestResolveRedirectUrl:
    """Tests for the URL redirect resolver."""

    def test_direct_url(self):
        url = "https://example.com/docs/page"
        assert _resolve_redirect_url(url) == url

    def test_single_redirect(self):
        url = (
            "https://community.instructure.com/home/leaving"
            "?allowTrusted=1"
            "&target=https%3A%2F%2Fexample.com%2Fdocs"
        )
        assert _resolve_redirect_url(url) == "https://example.com/docs"

    def test_double_redirect(self):
        """Instructure sometimes double-wraps redirect URLs."""
        url = (
            "https://community.instructure.com/home/leaving"
            "?allowTrusted=1"
            "&target=https%3A%2F%2Finstructure.vanillacommunities.com"
            "%2Fhome%2Fleaving%3FallowTrusted%3D1%26target%3D"
            "https%253A%252F%252Fcommunity.canvaslms.com%252Ft5"
            "%252FAdmin-Guide%252Fpage%252Fta-p%252F204"
        )
        resolved = _resolve_redirect_url(url)
        assert "community.canvaslms.com" in resolved
        assert "leaving" not in resolved

    def test_empty_url(self):
        assert _resolve_redirect_url("") == ""

    def test_none_url(self):
        assert _resolve_redirect_url(None) is None


# ============================================================================
# Tests for parse_canonical_page_html
# ============================================================================


# Mock HTML that mirrors the REAL structure observed on the canonical page.
# Key structural elements:
# - Content in .userContent container
# - H2 headings for sections
# - Tables wrapped in <div class="tableWrapper">
# - Config cells may have multiple <p> elements
# - Feature names may be links (doc_url) or plain text
# - Feature Previews table has an extra "User Group" column
# - Default Optional Features table has NO Configuration column

MOCK_HTML = """
<html>
<body>
<div class="userContent">
  <p>Intro text about feature options...</p>

  <h2 data-id="pending-feature-options"><strong>Pending Feature Options</strong></h2>
  <p>Pending features will eventually be enforced.</p>
  <div class="tableWrapper customized noScroll">
    <table>
      <tr>
        <th>Feature Option</th>
        <th>Summary</th>
        <th>Configuration</th>
        <th>Release Notes</th>
      </tr>
      <tr>
        <td>Disable Classic Quiz Creation</td>
        <td>Removes the ability for instructors to create Classic Quizzes.</td>
        <td><p>Account (Disabled/Unlocked)</p></td>
        <td><a href="https://community.instructure.com/home/leaving?allowTrusted=1&target=https%3A%2F%2Fexample.com%2Frelease1">Canvas Deploy Notes (2022-09-28)</a></td>
      </tr>
      <tr>
        <td><a href="https://community.instructure.com/home/leaving?allowTrusted=1&target=https%3A%2F%2Fexample.com%2Fnew-quizzes-doc">New Quizzes</a></td>
        <td>New Quizzes LTI assessment engine that replaces Classic Quizzes.</td>
        <td><p>Account (Disabled/Unlocked)</p></td>
        <td><a href="https://example.com/release2">Canvas Release Notes (2018-07-14)</a></td>
      </tr>
      <tr>
        <td>Calendar Event Title Tooltip</td>
        <td>Displays a tooltip for calendar events if the title doesn't fit.</td>
        <td><p>Account (Disabled)</p></td>
        <td><a href="https://example.com/release3">Canvas Deploy Notes (2022-06-22)</a></td>
      </tr>
    </table>
  </div>

  <h2 data-id="optional-features"><strong>Optional Features</strong></h2>
  <p>Optional features will never be enforced.</p>
  <div class="tableWrapper customized noScroll">
    <table>
      <tr>
        <th>Feature Option</th>
        <th>Summary</th>
        <th>Configuration</th>
        <th>Release Notes</th>
      </tr>
      <tr>
        <td><a href="https://community.instructure.com/home/leaving?allowTrusted=1&target=https%3A%2F%2Fexample.com%2Fmastery-scales-doc">Account and Course Level Outcome Mastery Scales</a></td>
        <td>Allow setting account and course-level mastery scales.</td>
        <td><p>Must be configured by a Customer Success Manager (CSM)</p></td>
        <td><a href="https://example.com/release4">Canvas Release Notes (2020-12-19)</a></td>
      </tr>
      <tr>
        <td><a href="https://community.instructure.com/home/leaving?allowTrusted=1&target=https%3A%2F%2Fexample.com%2Foutcome-extra-credit-doc">Allow Outcome Extra Credit</a></td>
        <td>Allows instructors to award more than the maximum possible score.</td>
        <td><p>Account (Disabled/Unlocked)</p></td>
        <td><a href="https://example.com/release5">Canvas Release Notes (2018-04-21)</a></td>
      </tr>
      <tr>
        <td>Search for Courses</td>
        <td>Allows searching for courses in the account.</td>
        <td><p>Account (Disabled/Locked)</p><p>Course (Disabled)</p></td>
        <td><a href="https://example.com/release6">Canvas Release Notes (2024-01-20)</a></td>
      </tr>
      <tr>
        <td>Student Analysis Report</td>
        <td>Provides student analysis reporting capabilities.</td>
        <td><p>Account (Disabled/Unlocked)</p><p>Course (Disabled)</p><p>&nbsp;</p></td>
        <td><a href="https://example.com/release7">Canvas Release Notes (2024-03-16)</a></td>
      </tr>
      <tr>
        <td><a href="https://community.instructure.com/home/leaving?allowTrusted=1&target=https%3A%2F%2Fexample.com%2Fyt-migration-doc">YouTube Content Migration</a></td>
        <td>Migrates embedded YouTube videos in Canvas to Studio.</td>
        <td><p>Account</p><p>(Disabled/Unlocked)</p></td>
        <td><a href="https://example.com/release8">Canvas Release Notes (2025-01-18)</a></td>
      </tr>
      <tr>
        <td>Account/Course Disabled Feature</td>
        <td>A feature at both account and course level.</td>
        <td><p>Account/Course (Disabled/Unlocked)</p></td>
        <td><a href="https://example.com/release9">Canvas Release Notes (2023-05-06)</a></td>
      </tr>
      <tr>
        <td>User Setting Feature</td>
        <td>A feature configured at user settings level.</td>
        <td><p>User Settings (Disabled)</p></td>
        <td><a href="https://example.com/release10">Canvas Release Notes (2023-06-17)</a></td>
      </tr>
    </table>
  </div>

  <h2 data-id="default-optional-features"><strong>Default Optional Features</strong></h2>
  <p>Default optional features are enabled for each account by default.</p>
  <div class="tableWrapper customized noScroll">
    <table>
      <tr>
        <th>Feature Option</th>
        <th>Summary</th>
        <th>Release Notes</th>
      </tr>
      <tr>
        <td><a href="https://community.instructure.com/home/leaving?allowTrusted=1&target=https%3A%2F%2Fexample.com%2Fadmin-analytics-doc">Admin Analytics</a></td>
        <td>Allows Admins to view, filter, and download data about Canvas usage.</td>
        <td><a href="https://example.com/release11">Canvas Release Notes (2023-03-29)</a></td>
      </tr>
      <tr>
        <td>Comment Library</td>
        <td>Allows instructors to save and reuse comments in SpeedGrader.</td>
        <td><a href="https://example.com/release12">Canvas Release Notes (2021-07-17)</a></td>
      </tr>
    </table>
  </div>

  <h2 data-id="feature-previews"><strong>Feature Previews</strong></h2>
  <p>Feature previews are in active development.</p>
  <p>Additional info about user groups.</p>
  <div class="tableWrapper customized noScroll">
    <table>
      <tr>
        <th>Feature Preview</th>
        <th>Summary</th>
        <th>Configuration</th>
        <th>Release Notes</th>
        <th>User Group</th>
      </tr>
      <tr>
        <td><a href="https://community.instructure.com/home/leaving?allowTrusted=1&target=https%3A%2F%2Fexample.com%2Fassignment-enhancements-doc">Assignment Enhancements</a></td>
        <td>Allows supported student assignments to display an improved interface.</td>
        <td><p>Account (Disabled/Unlocked)</p></td>
        <td><a href="https://example.com/release13">Canvas Release Notes (2020-01-18)</a></td>
        <td><a href="https://community.instructure.com/home/leaving?allowTrusted=1&target=https%3A%2F%2Fexample.com%2Fassignment-ug">Assignment Enhancement User Group</a></td>
      </tr>
      <tr>
        <td><a href="https://community.instructure.com/home/leaving?allowTrusted=1&target=https%3A%2F%2Fexample.com%2Fcourse-pacing-doc">Course Pacing</a></td>
        <td>Distributes due dates on a defined pace for rolling enrollments.</td>
        <td><p>Course (Disabled)</p></td>
        <td><a href="https://example.com/release14">Canvas Deploy Notes (2022-04-27)</a></td>
        <td><a href="https://community.instructure.com/home/leaving?allowTrusted=1&target=https%3A%2F%2Fexample.com%2Fcourse-pacing-ug">Course Pacing User Group</a></td>
      </tr>
      <tr>
        <td>Enhanced Rubrics</td>
        <td>Enhanced Rubrics provides an improved rubric creation and grading experience.</td>
        <td><p>Beta: Account/Course (Enabled/Unlocked)</p><p>Production: Account/Course (Disabled/Unlocked)</p></td>
        <td><a href="https://example.com/release15">Canvas Deploy Notes (2024-10-16)</a></td>
        <td><a href="https://community.instructure.com/home/leaving?allowTrusted=1&target=https%3A%2F%2Fexample.com%2Frubrics-ug">Enhanced Rubrics User Group</a></td>
      </tr>
      <tr>
        <td>Canvas Portfolio</td>
        <td>Canvas Portfolio is an ePortfolio tool integrated with Canvas.</td>
        <td><p>LTI Configuration Required</p></td>
        <td><a href="https://example.com/release16">Canvas Release Notes (2024-05-18)</a></td>
        <td></td>
      </tr>
      <tr>
        <td>Discussion Summaries</td>
        <td>Uses AI to give instructors summaries of discussion threads.</td>
        <td><p>Account (Disabled/Locked)</p></td>
        <td><a href="https://example.com/release17">Canvas Deploy Notes (2024-07-17)</a></td>
        <td><a href="https://community.instructure.com/home/leaving?allowTrusted=1&target=https%3A%2F%2Fexample.com%2Fdiscussion-summaries-ug">Discussion Summaries User Group</a></td>
      </tr>
    </table>
  </div>
</div>
</body>
</html>
"""


class TestParseCanonicalPageHtml:
    """Tests for the full HTML page parser."""

    @pytest.fixture
    def options(self):
        """Parse the mock HTML and return the list of options."""
        return parse_canonical_page_html(MOCK_HTML)

    def test_total_option_count(self, options):
        """All rows across all 4 sections should be parsed."""
        # 3 pending + 7 optional + 2 default optional + 5 preview = 17
        assert len(options) == 17

    # --- Pending Feature Options section ---

    def test_pending_count(self, options):
        pending = [o for o in options if o.will_be_enforced]
        assert len(pending) == 3

    def test_pending_disable_classic_quiz(self, options):
        opt = next(o for o in options if o.name == "Disable Classic Quiz Creation")
        assert opt.lifecycle_stage == "optional"
        assert opt.will_be_enforced is True
        assert opt.prod_account_state == "disabled_unlocked"
        assert opt.prod_course_state == "N/A"
        assert opt.doc_url is None  # no link in name cell
        assert opt.description == "Removes the ability for instructors to create Classic Quizzes."

    def test_pending_new_quizzes_has_doc_url(self, options):
        opt = next(
            o for o in options
            if o.name == "New Quizzes" and o.will_be_enforced
        )
        assert opt.doc_url is not None
        assert "new-quizzes-doc" in opt.doc_url

    def test_pending_calendar_tooltip_account_disabled(self, options):
        opt = next(o for o in options if o.name == "Calendar Event Title Tooltip")
        assert opt.prod_account_state == "disabled"
        assert opt.prod_course_state == "N/A"

    # --- Optional Features section ---

    def test_optional_count(self, options):
        optional_stable = [
            o for o in options
            if o.lifecycle_stage == "optional"
            and not o.will_be_enforced
            and o.name not in ("Admin Analytics", "Comment Library")  # default optional
        ]
        assert len(optional_stable) == 7

    def test_optional_csm_managed(self, options):
        opt = next(
            o for o in options
            if o.name == "Account and Course Level Outcome Mastery Scales"
        )
        assert opt.lifecycle_stage == "optional"
        assert opt.prod_account_state == "csm_managed"
        assert opt.doc_url is not None
        assert "mastery-scales-doc" in opt.doc_url

    def test_optional_multiline_account_locked_course(self, options):
        """Search for Courses: Account (Disabled/Locked) + Course (Disabled)."""
        opt = next(o for o in options if o.name == "Search for Courses")
        assert opt.prod_account_state == "disabled_locked"
        assert opt.prod_course_state == "disabled"

    def test_optional_multiline_with_nbsp(self, options):
        """Student Analysis Report: multiline with trailing &nbsp;."""
        opt = next(o for o in options if o.name == "Student Analysis Report")
        assert opt.prod_account_state == "disabled_unlocked"
        assert opt.prod_course_state == "disabled"

    def test_optional_split_account_state(self, options):
        """YouTube Content Migration: Account\\n(Disabled/Unlocked) typo."""
        opt = next(o for o in options if o.name == "YouTube Content Migration")
        assert opt.prod_account_state == "disabled_unlocked"
        assert opt.prod_course_state == "N/A"
        assert opt.doc_url is not None

    def test_optional_account_course_combined(self, options):
        opt = next(o for o in options if o.name == "Account/Course Disabled Feature")
        assert opt.prod_account_state == "disabled_unlocked"
        assert opt.prod_course_state == "disabled"

    def test_optional_user_setting(self, options):
        opt = next(o for o in options if o.name == "User Setting Feature")
        assert opt.prod_account_state == "user_setting"

    # --- Default Optional Features section ---

    def test_default_optional_count(self, options):
        default_opt = [
            o for o in options
            if o.name in ("Admin Analytics", "Comment Library")
        ]
        assert len(default_opt) == 2

    def test_default_optional_enabled_unlocked(self, options):
        """Default optional features should be enabled_unlocked (no config column)."""
        opt = next(o for o in options if o.name == "Admin Analytics")
        assert opt.lifecycle_stage == "optional"
        assert opt.prod_account_state == "enabled_unlocked"
        assert opt.prod_course_state == "N/A"
        assert opt.doc_url is not None
        assert "admin-analytics-doc" in opt.doc_url

    def test_default_optional_no_doc_url(self, options):
        """Comment Library has no link in name cell."""
        opt = next(o for o in options if o.name == "Comment Library")
        assert opt.lifecycle_stage == "optional"
        assert opt.prod_account_state == "enabled_unlocked"
        assert opt.doc_url is None

    # --- Feature Previews section ---

    def test_preview_count(self, options):
        previews = [o for o in options if o.lifecycle_stage == "feature_preview"]
        assert len(previews) == 5

    def test_preview_assignment_enhancements(self, options):
        opt = next(o for o in options if o.name == "Assignment Enhancements")
        assert opt.lifecycle_stage == "feature_preview"
        assert opt.prod_account_state == "disabled_unlocked"
        assert opt.doc_url is not None
        assert "assignment-enhancements-doc" in opt.doc_url
        assert opt.user_group_url is not None
        assert "assignment-ug" in opt.user_group_url

    def test_preview_course_pacing(self, options):
        opt = next(o for o in options if o.name == "Course Pacing")
        assert opt.lifecycle_stage == "feature_preview"
        assert opt.prod_account_state == "N/A"
        assert opt.prod_course_state == "disabled"
        assert opt.user_group_url is not None

    def test_preview_enhanced_rubrics_beta_prod_split(self, options):
        """Enhanced Rubrics has separate beta and prod configuration."""
        opt = next(o for o in options if o.name == "Enhanced Rubrics")
        assert opt.lifecycle_stage == "feature_preview"
        assert opt.beta_account_state == "enabled_unlocked"
        assert opt.beta_course_state == "enabled"
        assert opt.prod_account_state == "disabled_unlocked"
        assert opt.prod_course_state == "disabled"
        assert opt.user_group_url is not None

    def test_preview_canvas_portfolio_lti(self, options):
        opt = next(o for o in options if o.name == "Canvas Portfolio")
        assert opt.lifecycle_stage == "feature_preview"
        assert opt.prod_account_state == "lti_required"
        assert opt.user_group_url is None  # empty user group cell

    def test_preview_discussion_summaries_locked(self, options):
        opt = next(o for o in options if o.name == "Discussion Summaries")
        assert opt.lifecycle_stage == "feature_preview"
        assert opt.prod_account_state == "disabled_locked"
        assert opt.user_group_url is not None

    # --- User group URL resolution ---

    def test_user_group_urls_resolved(self, options):
        """User group URLs should be resolved through redirect wrappers."""
        opt = next(o for o in options if o.name == "Assignment Enhancements")
        # The URL should be resolved, not the /home/leaving redirect
        assert "leaving" not in opt.user_group_url

    # --- Doc URL resolution ---

    def test_doc_urls_resolved(self, options):
        """Doc URLs should be resolved through redirect wrappers."""
        opt = next(o for o in options if o.name == "Admin Analytics")
        assert "leaving" not in opt.doc_url


class TestParseCanonicalPageHtmlEdgeCases:
    """Edge cases for the HTML parser."""

    def test_empty_html(self):
        options = parse_canonical_page_html("")
        assert options == []

    def test_no_user_content(self):
        html = "<html><body><p>No content here</p></body></html>"
        options = parse_canonical_page_html(html)
        assert options == []

    def test_missing_table_after_heading(self):
        html = """
        <div class="userContent">
          <h2>Pending Feature Options</h2>
          <p>No table here!</p>
          <h2>Optional Features</h2>
        </div>
        """
        options = parse_canonical_page_html(html)
        assert options == []

    def test_unrecognized_heading_ignored(self):
        html = """
        <div class="userContent">
          <h2>Some Other Section</h2>
          <div class="tableWrapper">
            <table>
              <tr><th>Name</th><th>Summary</th></tr>
              <tr><td>Test</td><td>Test desc</td></tr>
            </table>
          </div>
          <h2>Pending Feature Options</h2>
          <div class="tableWrapper">
            <table>
              <tr><th>Feature Option</th><th>Summary</th><th>Configuration</th><th>Release Notes</th></tr>
              <tr>
                <td>Real Feature</td>
                <td>A real feature.</td>
                <td><p>Account (Disabled/Unlocked)</p></td>
                <td>Notes</td>
              </tr>
            </table>
          </div>
        </div>
        """
        options = parse_canonical_page_html(html)
        assert len(options) == 1
        assert options[0].name == "Real Feature"

    def test_empty_row_skipped(self):
        html = """
        <div class="userContent">
          <h2>Pending Feature Options</h2>
          <div class="tableWrapper">
            <table>
              <tr><th>Feature Option</th><th>Summary</th><th>Configuration</th><th>Release Notes</th></tr>
              <tr><td></td><td></td><td></td><td></td></tr>
              <tr>
                <td>Real Feature</td>
                <td>A real feature.</td>
                <td><p>Account (Disabled/Unlocked)</p></td>
                <td>Notes</td>
              </tr>
            </table>
          </div>
        </div>
        """
        options = parse_canonical_page_html(html)
        assert len(options) == 1
        assert options[0].name == "Real Feature"

    def test_strong_wrapped_heading(self):
        """Real page wraps heading text in <strong> tags."""
        html = """
        <div class="userContent">
          <h2 data-id="pending-feature-options"><strong>Pending Feature Options</strong></h2>
          <div class="tableWrapper">
            <table>
              <tr><th>Feature Option</th><th>Summary</th><th>Configuration</th><th>Release Notes</th></tr>
              <tr>
                <td>Test Feature</td>
                <td>Test description.</td>
                <td><p>Account (Disabled/Unlocked)</p></td>
                <td>Notes</td>
              </tr>
            </table>
          </div>
        </div>
        """
        options = parse_canonical_page_html(html)
        assert len(options) == 1
        assert options[0].lifecycle_stage == "optional"
        assert options[0].will_be_enforced is True


class TestExtractConfigTextFromCell:
    """Tests for the config text cell extraction helper."""

    def test_single_paragraph(self):
        from bs4 import BeautifulSoup
        html = "<td><p>Account (Disabled/Unlocked)</p></td>"
        td = BeautifulSoup(html, "html.parser").find("td")
        assert _extract_config_text_from_cell(td) == "Account (Disabled/Unlocked)"

    def test_multiple_paragraphs(self):
        from bs4 import BeautifulSoup
        html = "<td><p>Account (Disabled/Locked)</p><p>Course (Disabled)</p></td>"
        td = BeautifulSoup(html, "html.parser").find("td")
        result = _extract_config_text_from_cell(td)
        assert "Account (Disabled/Locked)" in result
        assert "Course (Disabled)" in result
        assert "\n" in result

    def test_paragraphs_with_nbsp(self):
        from bs4 import BeautifulSoup
        html = "<td><p>Account (Disabled/Unlocked)</p><p>Course (Disabled)</p><p>&nbsp;</p></td>"
        td = BeautifulSoup(html, "html.parser").find("td")
        result = _extract_config_text_from_cell(td)
        lines = [l for l in result.split("\n") if l.strip()]
        assert len(lines) >= 2

    def test_plain_text_no_paragraphs(self):
        from bs4 import BeautifulSoup
        html = "<td>Account (Disabled/Unlocked)</td>"
        td = BeautifulSoup(html, "html.parser").find("td")
        assert _extract_config_text_from_cell(td) == "Account (Disabled/Unlocked)"
