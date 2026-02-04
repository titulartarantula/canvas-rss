"""Canonical constants for canvas-rss."""

CONTENT_TYPES = {
    'release_note',
    'deploy_note',
    'changelog',
    'blog',
    'question',
    'reddit',
    'status',
}

CANVAS_FEATURES = {
    # Core Course Features
    'announcements': 'Announcements',
    'assignments': 'Assignments',
    'discussions': 'Discussions',
    'files': 'Files',
    'modules': 'Modules',
    'pages': 'Pages',
    'classic_quizzes': 'Quizzes (Classic)',
    'new_quizzes': 'New Quizzes',
    'syllabus': 'Syllabus',

    # Grading & Assessment
    'gradebook': 'Gradebook',
    'speedgrader': 'SpeedGrader',
    'rubrics': 'Rubrics',
    'outcomes': 'Outcomes',
    'mastery_paths': 'Mastery Paths',
    'peer_reviews': 'Peer Reviews',

    # Collaboration
    'collaborations': 'Collaborations',
    'conferences': 'Conferences',
    'groups': 'Groups',
    'chat': 'Chat',

    # Communication
    'inbox': 'Inbox',
    'calendar': 'Calendar',
    'notifications': 'Notifications',

    # User Interface
    'dashboard': 'Dashboard',
    'global_navigation': 'Global Navigation',
    'profile_settings': 'Profile and User Settings',
    'rich_content_editor': 'Rich Content Editor (RCE)',

    # Portfolio & Showcase
    'eportfolios': 'ePortfolios',
    'student_eportfolios': 'Canvas Student ePortfolios',

    # Analytics & Data
    'canvas_analytics': 'Canvas Analytics',
    'canvas_data_services': 'Canvas Data Services',

    # Add-on Products
    'canvas_catalog': 'Canvas Catalog',
    'canvas_studio': 'Canvas Studio',
    'canvas_commons': 'Canvas Commons',
    'student_pathways': 'Canvas Student Pathways',
    'mastery_connect': 'Mastery Connect',
    'parchment_badges': 'Parchment Digital Badges',

    # Mobile
    'canvas_mobile': 'Canvas Mobile',

    # Administration
    'course_import': 'Course Import Tool',
    'blueprint_courses': 'Blueprint Courses',
    'sis_import': 'SIS Import',
    'external_apps_lti': 'External Apps (LTI)',
    'api': 'Web Services / API',
    'account_settings': 'Account Settings',
    'themes_branding': 'Themes/Branding',
    'authentication': 'Authentication',

    # Specialized
    'canvas_elementary': 'Canvas for Elementary',

    # Catch-all
    'general': 'General',
}

FEATURE_OPTION_STATUSES = {
    'pending',          # Announced but not yet available
    'preview',          # Feature preview / beta
    'optional',         # Available but disabled by default
    'default_optional', # Enabled by default, can be disabled
    'released',         # Fully released, no longer a feature option
}

MENTION_TYPES = {
    'announces',   # Content announces this feature/option
    'discusses',   # Content discusses/explains
    'questions',   # Content asks about
    'feedback',    # Content provides feedback/complaints
}
