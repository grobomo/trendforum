const API_BASE = '/api';

let authToken: string | null = localStorage.getItem('tf_token');

export function setToken(token: string) {
  authToken = token;
  localStorage.setItem('tf_token', token);
}

export function getToken(): string | null {
  return authToken;
}

export function clearToken() {
  authToken = null;
  localStorage.removeItem('tf_token');
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };

  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(body.error || `Request failed: ${res.status}`);
  }

  return res.json();
}

// --- Types ---

export interface SubforumInfo {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  postCount: number;
}

export interface PostSummary {
  id: number;
  title: string;
  body: string | null;
  linkUrl: string | null;
  score: number;
  upvotes: number;
  downvotes: number;
  commentCount: number;
  createdAt: string;
  hotScore: number;
  subforumSlug: string;
  subforumName?: string;
}

export interface CommentNode {
  id: number;
  displayName: string;
  body: string;
  score: number;
  createdAt: string;
  parentId: number | null;
  profileId: number | null;
  children: CommentNode[];
}

export interface PostDetailData {
  id: number;
  title: string;
  body: string | null;
  linkUrl: string | null;
  score: number;
  upvotes: number;
  downvotes: number;
  createdAt: string;
  subforum: { id: number; slug: string; name: string };
  comments: CommentNode[];
  commentCount: number;
}

export interface PostsResponse {
  posts: PostSummary[];
  page: number;
  limit: number;
  subforum?: { id: number; slug: string; name: string; description?: string | null };
}

export interface Profile {
  id: number;
  username: string;
  bio: string | null;
  avatarUrl: string | null;
  createdAt: string;
}

// --- Auth ---

export async function verifyPassword(password: string, admin = false): Promise<{ token: string }> {
  return request('/auth/verify', {
    method: 'POST',
    body: JSON.stringify({ password, admin }),
  });
}

// --- Subforums ---

export async function getSubforums(): Promise<SubforumInfo[]> {
  return request('/subforums');
}

export async function getSubforum(slug: string): Promise<SubforumInfo> {
  return request(`/subforums/${slug}`);
}

// --- Posts ---

export async function getAllPosts(sort = 'hot', page = 1): Promise<any[]> {
  return request(`/posts?sort=${sort}&page=${page}`);
}

export async function getSubforumPosts(slug: string, sort = 'hot', page = 1): Promise<any[]> {
  return request(`/subforums/${slug}/posts?sort=${sort}&page=${page}`);
}

export async function getPost(id: number): Promise<PostDetailData> {
  return request(`/posts/${id}`);
}

export async function createPost(data: {
  subforumId: number;
  title: string;
  body?: string;
  linkUrl?: string;
}): Promise<{ id: number; subforumSlug: string }> {
  return request('/posts', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// --- Comments ---

export async function createComment(
  postId: number,
  body: string,
  parentId?: number
): Promise<{ id: number }> {
  return request(`/posts/${postId}/comments`, {
    method: 'POST',
    body: JSON.stringify({ body, parentId }),
  });
}

// --- Votes ---

export async function vote(data: {
  postId?: number;
  commentId?: number;
  value: 1 | -1;
}): Promise<{ action: string; voted: number | null; score: number }> {
  return request('/vote', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// --- Reports ---

export async function report(data: {
  postId?: number;
  commentId?: number;
  reason: string;
}): Promise<{ id: number; message: string }> {
  return request('/report', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// --- Mod ---

export async function getReports(): Promise<any[]> {
  return request('/mod/reports');
}

export async function modAction(data: {
  action: string;
  targetId: number;
  targetType: string;
  reason?: string;
}): Promise<any> {
  return request('/mod/action', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// --- Search ---

export async function searchPosts(q: string, page = 1): Promise<any[]> {
  return request(`/search?q=${encodeURIComponent(q)}&page=${page}`);
}

// --- Profiles ---

export async function createProfile(username: string, pin: string): Promise<{ token: string; profile: Profile }> {
  return request('/profile/create', {
    method: 'POST',
    body: JSON.stringify({ username, pin }),
  });
}

export async function claimProfile(username: string, pin: string): Promise<{ token: string; profile: Profile }> {
  return request('/profile/claim', {
    method: 'POST',
    body: JSON.stringify({ username, pin }),
  });
}

export async function getProfile(): Promise<{ profile: Profile | null }> {
  return request('/profile');
}

export async function updateProfile(data: { bio?: string; avatarUrl?: string }): Promise<Profile> {
  return request('/profile', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function getPublicProfile(username: string): Promise<Profile> {
  return request(`/profile/${encodeURIComponent(username)}`);
}

export async function getProfileComments(username: string, page = 1): Promise<{ comments: any[]; total: number }> {
  return request(`/profile/${encodeURIComponent(username)}/comments?page=${page}`);
}

// --- Notifications ---

export interface NotificationItem {
  id: number;
  type: string;
  message: string;
  linkUrl: string;
  read: boolean;
  createdAt: string;
}

export async function getNotifications(unreadOnly = false, limit = 50): Promise<{ notifications: NotificationItem[]; unreadCount: number }> {
  return request(`/notifications?unreadOnly=${unreadOnly}&limit=${limit}`);
}

export async function getNotificationCount(): Promise<{ unreadCount: number }> {
  return request('/notifications/count');
}

export async function markNotificationsRead(ids?: number[]): Promise<void> {
  await request('/notifications/read', {
    method: 'POST',
    body: JSON.stringify(ids ? { ids } : { all: true }),
  });
}

export async function deleteNotification(id: number): Promise<{ ok: boolean }> {
  return request(`/notifications/${id}`, { method: 'DELETE' });
}

// --- Namespaced API object (used by newer components) ---

export const api = {
  posts: {
    list: getAllPosts,
    bySubforum: getSubforumPosts,
    get: getPost,
    create: createPost,
  },
  comments: {
    create: (postId: number, data: { body: string; parentId?: number }) =>
      createComment(postId, data.body, data.parentId),
  },
  search: {
    query: searchPosts,
  },
  profile: {
    get: (username: string) => getPublicProfile(username).then(profile => ({ profile })),
    me: () => getProfile(),
    create: createProfile,
    claim: claimProfile,
    update: updateProfile,
  },
};
