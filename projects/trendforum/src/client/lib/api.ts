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

// --- Posts ---

export async function getAllPosts(sort = 'hot', page = 1): Promise<PostsResponse> {
  return request(`/posts?sort=${sort}&page=${page}`);
}

export async function getSubforumPosts(slug: string, sort = 'hot', page = 1): Promise<PostsResponse> {
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
