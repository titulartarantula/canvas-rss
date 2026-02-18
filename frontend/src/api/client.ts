import axios from 'axios';
import type {
  DashboardData,
  Feature,
  FeatureOption,
  FeatureOptionDetail,
  FeatureSetting,
  FeatureSettingDetail,
  Release,
  SearchResults,
  Announcement,
  AnnouncementDetail,
  CommunityPost,
} from '../types';

const api = axios.create({
  baseURL: '/api',
});

export const dashboardApi = {
  get: async (date?: string): Promise<DashboardData> => {
    const params = date ? { date } : {};
    const { data } = await api.get('/dashboard', { params });
    return data;
  },
};

export const featuresApi = {
  list: async (category?: string): Promise<{ features: Feature[] }> => {
    const params = category ? { category } : {};
    const { data } = await api.get('/features', { params });
    return data;
  },
  get: async (featureId: string): Promise<Feature & { options: FeatureOption[]; settings: FeatureSetting[]; announcements: Announcement[]; community_posts: CommunityPost[] }> => {
    const { data } = await api.get(`/features/${featureId}`);
    return data;
  },
};

export const optionsApi = {
  list: async (params?: {
    status?: string;
    feature?: string;
    sort?: string;
  }): Promise<{ options: FeatureOption[] }> => {
    const { data } = await api.get('/options', { params });
    return data;
  },
  get: async (optionId: string): Promise<FeatureOptionDetail> => {
    const { data } = await api.get(`/options/${optionId}`);
    return data;
  },
};

export const settingsApi = {
  list: async (params?: {
    status?: string;
    feature?: string;
    sort?: string;
  }): Promise<{ settings: FeatureSetting[] }> => {
    const { data } = await api.get('/settings', { params });
    return data;
  },
  get: async (settingId: string): Promise<FeatureSettingDetail> => {
    const { data } = await api.get(`/settings/${settingId}`);
    return data;
  },
};

export const releasesApi = {
  list: async (params?: {
    type?: string;
    year?: number;
    search?: string;
  }): Promise<{ releases: Release[] }> => {
    const { data } = await api.get('/releases', { params });
    return data;
  },
  get: async (contentId: string): Promise<Release> => {
    const { data } = await api.get(`/releases/${contentId}`);
    return data;
  },
};

export const announcementsApi = {
  get: async (id: number): Promise<AnnouncementDetail> => {
    const { data } = await api.get(`/announcements/${id}`);
    return data;
  },
};

export const searchApi = {
  search: async (q: string): Promise<SearchResults> => {
    const { data } = await api.get('/search', { params: { q } });
    return data;
  },
};
