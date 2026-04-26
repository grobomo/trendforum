const BASE = '/api';

let authToken: string | null = null;

export function setToken(token: string | null) {
  authToken = token;
  if (token) {
    sessionStorage.setItem('tf_token', token);
  } else {
    sessionStorage.removeItem('tf_token');
  }
}

export function getToken(): string | null {
  if (!authToken) {
    authToken = sessionStorage.getItem('tf_token');
  }
  return authToken;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed: ${res.status}`);
  }

  return res.json();
}

export const api = {
  auth: {
    verify: (password: string) =>
      request<{ token: string }>('/auth/verify', {
        method: 'POST',
        body: JSON.stringify({ password }),
      }),
  },
  subforums: {
    list: () => request<any[]>('/subforums'),
  },
  posts: {
    list: (sort = 'hot', page = 1) =>
      request<any[]>(`/posts?sort=${sort}&page=${page}`),
    bySubforum: (slug: string, sort = 'hot', page = 1) =>
      request<any[]>(`/subforums/${slug}/posts?sort=${sort}&page=${page}`),
    get: (id: number) => request<any>(`/posts/${id}`),
    create: (data: { subforumId: number; title: string; body?: string; linkUrl?: string }) =>
      request<any>('/posts', { method: 'POST', body: JSON.stringify(data) }),
  },
  comments: {
    create: (postId: number, data: { body: string; parentId?: number }) =>
      request<any>(`/posts/${postId}/comments`, { method: 'POST', body: JSON.stringify(data) }),
  },
  votes: {
    vote: (data: { postId?: number; commentId?: number; value: 1 | -1 }) =>
      request<{ voted: number | null }>('/vote', { method: 'POST', body: JSON.stringify(data) }),
  },
  reports: {
    create: (data: { postId?: number; commentId?: number; reason: string }) =>
      request<any>('/report', { method: 'POST', body: JSON.stringify(data) }),
  },
};
