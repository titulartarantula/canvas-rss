export interface Feature {
  feature_id: string;
  name: string;
  description: string | null;
  status: string;
  option_count?: number;
  preview_count?: number;
  pending_count?: number;
  optional_count?: number;
  status_summary?: string;
}

export interface FeatureOption {
  option_id: string;
  feature_id: string;
  canonical_name: string | null;
  name: string;
  description: string | null;
  meta_summary: string | null;
  status: string;
  beta_date: string | null;
  production_date: string | null;
  deprecation_date: string | null;
  config_level: string | null;
  default_state: string | null;
  user_group_url: string | null;
  first_seen: string | null;
  last_seen: string | null;
  feature_name?: string;
}

export interface FeatureOptionDetail extends FeatureOption {
  feature: {
    feature_id: string;
    name: string;
    description: string | null;
  };
  configuration: {
    config_level: string | null;
    default_state: string | null;
    enable_location_account: string | null;
    enable_location_course: string | null;
    subaccount_config: boolean | null;
    permissions: string | null;
    affected_areas: string | null;
    affects_ui: boolean | null;
  };
  announcements: Announcement[];
  community_posts: CommunityPost[];
}

export interface Announcement {
  id: number;
  h4_title: string;
  section: string | null;
  category: string | null;
  description: string | null;
  implications: string | null;
  announced_at: string;
  release_title?: string;
  release_url?: string;
  option_id?: string;
  beta_date?: string | null;
  production_date?: string | null;
  option_status?: string;
  enable_location_account?: string | null;
  enable_location_course?: string | null;
  subaccount_config?: boolean | null;
  permissions?: string | null;
  affected_areas?: string | null;
  affects_ui?: boolean | null;
}

export interface CommunityPost {
  source_id: string;
  url: string;
  title: string;
  content_type: string;
  summary: string | null;
  first_posted: string;
  mention_type?: string;
}

export interface Release {
  source_id: string;
  url: string;
  title: string;
  content_type: string;
  summary: string | null;
  first_posted: string | null;
  published_date: string | null;
  announcement_count?: number;
  announcements?: Announcement[];
  upcoming_changes?: UpcomingChange[];
}

export interface UpcomingChange {
  change_date: string;
  description: string;
}

export interface DashboardData {
  release_note: Release | null;
  deploy_note: Release | null;
  upcoming_changes: UpcomingChange[];
  recent_activity: CommunityPost[];
}

export interface SearchResults {
  features: Feature[];
  options: FeatureOption[];
  content: CommunityPost[];
}
