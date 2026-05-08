import { getToken } from "@/lib/auth";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function api<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`/api${path}`, { ...options, headers });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = formatApiDetail(
      payload && typeof payload === "object" && "detail" in payload
        ? (payload as { detail: unknown }).detail
        : null
    );
    throw new ApiError(detail, response.status);
  }
  return payload as T;
}

function formatApiDetail(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return null;
      })
      .filter(Boolean);

    if (messages.length > 0) {
      return messages.join("; ");
    }
  }

  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }

  return "Запрос не удался";
}

export type FileRead = {
  id: string;
  name: string;
  size_bytes: number;
  status: string;
  current_version_number: number;
  folder_id: string | null;
  content_type: string;
  created_at: string;
};

export type FolderRead = {
  id: string;
  name: string;
  parent_id: string | null;
  created_at: string;
};

export type LoginResponse = { access_token: string; token_type: string };

export type UserRead = {
  id: string;
  email: string;
  full_name: string;
  role: string;
};

export type UploadInitiateResponse = {
  upload_session_id: string;
  file_id: string;
  provider_upload_id: string;
  bucket: string;
  object_key: string;
  target_version_number: number;
  part_size: number;
  total_parts: number;
};

export type UploadPartUrl = { part_number: number; url: string };
export type UploadPartUrlResponse = {
  upload_session_id: string;
  urls: UploadPartUrl[];
};

export type ShareLinkRead = {
  id: string;
  token: string;
  is_active: boolean;
  expires_at: string | null;
  max_downloads: number | null;
  download_count: number;
};

export type StorageStats = {
  files_count: number;
  total_size_bytes: number;
};
