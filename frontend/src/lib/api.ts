import { useAuthStore } from "./auth";

const API_URL =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? "http://localhost:8000/api/v1" : "/api/v1");

type ApiOptions = RequestInit & {
  auth?: boolean;
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function formatLocation(location: unknown) {
  if (!Array.isArray(location)) {
    return "";
  }

  const labels: Record<string, string> = {
    access_token: "Access token",
    body: "Mensaje",
    business_account_id: "Business account ID",
    phone_number_id: "Phone number ID",
    to: "Destino",
    verify_token: "Verify token",
  };

  return location
    .filter((piece) => piece !== "body")
    .map((piece) => labels[String(piece)] ?? String(piece))
    .join(" > ");
}

function formatErrorDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (!isRecord(item)) {
          return "";
        }
        const location = formatLocation(item.loc);
        const message = typeof item.msg === "string" ? item.msg : "";
        return location && message ? `${location}: ${message}` : message;
      })
      .filter(Boolean);
    return messages.join(" | ") || fallback;
  }

  if (isRecord(detail)) {
    if (typeof detail.message === "string") {
      return detail.message;
    }
    if (typeof detail.msg === "string") {
      return detail.msg;
    }
    if (typeof detail.error === "string") {
      return detail.error;
    }
  }

  return fallback;
}

function formatApiError(payload: unknown, fallback: string) {
  if (!isRecord(payload)) {
    return fallback;
  }
  return formatErrorDetail(payload.detail ?? payload.message ?? payload.error, fallback);
}

function resolveBaseUrl(baseUrl: string) {
  const raw = baseUrl.trim();
  if (!raw) {
    return window.location.origin;
  }
  if (raw.startsWith("http://") || raw.startsWith("https://")) {
    return raw.replace(/\/$/, "");
  }
  const origin = window.location.origin.replace(/\/$/, "");
  if (raw.startsWith("/")) {
    return `${origin}${raw}`;
  }
  return `${origin}/${raw}`;
}

function joinUrl(baseUrl: string, path: string) {
  const normalizedBase = resolveBaseUrl(baseUrl).replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

async function readJsonResponse<T>(response: Response, path: string): Promise<T> {
  const contentType = response.headers.get("Content-Type") ?? "";
  if (!contentType.includes("application/json")) {
    throw new Error(`La ruta ${path} no respondio JSON. Revisa el enrutamiento de la API.`);
  }
  return response.json() as Promise<T>;
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const token = useAuthStore.getState().token;
  const headers = new Headers(options.headers);
  const hasFormDataBody = options.body instanceof FormData;
  if (!hasFormDataBody && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (options.auth !== false && token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(joinUrl(API_URL, path), {
    ...options,
    headers,
  });
  if (!response.ok) {
    const detail = await readJsonResponse<unknown>(response, path).catch(() => ({
      detail: response.statusText,
    }));
    if (response.status === 401 && options.auth !== false) {
      useAuthStore.getState().setToken(null);
      throw new Error("Sesion expirada. Ingresa de nuevo.");
    }
    throw new ApiError(response.status, formatApiError(detail, "Error de API"));
  }
  return readJsonResponse<T>(response, path);
}

export function realtimeUrl(path: string) {
  const socketBase = joinUrl(API_URL, path).replace(/^https?:/, window.location.protocol === "https:" ? "wss:" : "ws:");
  return socketBase;
}
