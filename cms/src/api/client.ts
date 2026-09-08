export const API_BASE = '';

export class ApiError extends Error {
  status: number;
  data?: any;
  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // If body is FormData or URLSearchParams, don't set Content-Type so browser sets it correctly
  if (!(options.body instanceof FormData) && !(options.body instanceof URLSearchParams)) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return {} as T;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(response.status, data?.detail || response.statusText, data);
  }

  return data as T;
}

export const api = {
  login: (data: URLSearchParams) => 
    request<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: data,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    }),
    
  getMe: () => request<any>('/auth/me'),
  
  getShows: (params?: Record<string, any>) => {
    const qs = new URLSearchParams();
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined && v !== null && v !== '') qs.append(k, String(v));
      }
    }
    const q = qs.toString();
    return request<any>(`/admin/shows${q ? `?${q}` : ''}`);
  },
  getShow: (id: string) => request<any>(`/admin/shows/${id}`),
  createShow: (data: any) => request<any>('/admin/shows', { method: 'POST', body: JSON.stringify(data) }),
  updateShow: (id: string, data: any) => request<any>(`/admin/shows/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteShow: (id: string) => request<any>(`/admin/shows/${id}`, { method: 'DELETE' }),

  getSeasons: (showId: string) => request<any>(`/admin/shows/${showId}/seasons`),
  createSeason: (showId: string, data: any) => request<any>(`/admin/shows/${showId}/seasons`, { method: 'POST', body: JSON.stringify(data) }),
  updateSeason: (id: string, data: any) => request<any>(`/admin/seasons/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSeason: (id: string) => request<any>(`/admin/seasons/${id}`, { method: 'DELETE' }),

  getEpisodes: (seasonId: string) => request<any>(`/admin/seasons/${seasonId}/episodes`),
  createEpisode: (seasonId: string, data: any) => request<any>(`/admin/seasons/${seasonId}/episodes`, { method: 'POST', body: JSON.stringify(data) }),
  updateEpisode: (id: string, data: any) => request<any>(`/admin/episodes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteEpisode: (id: string) => request<any>(`/admin/episodes/${id}`, { method: 'DELETE' }),

  uploadArtwork: (data: FormData) => request<any>('/admin/artwork', { method: 'POST', body: data }),
  deleteArtwork: (id: string) => request<any>(`/admin/artwork/${id}`, { method: 'DELETE' }),

  getValidationReport: () => request<any>('/admin/validation-report'),
  publishCatalog: () => request<any>('/admin/catalog/publish', { method: 'POST' }),
  getPublishRuns: () => request<any>('/admin/publish-runs'),
};
