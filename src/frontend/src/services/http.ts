import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

const DJANGO_API_URL = import.meta.env.VITE_DJANGO_API_URL || "http://127.0.0.1:8000";
const FASTAPI_URL = import.meta.env.VITE_FASTAPI_URL || "http://127.0.0.1:8001";
const POSTGRAPHQL_URL =
  import.meta.env.VITE_POSTGRAPHQL_URL ||
  import.meta.env.VITE_GRAPHQL_URL ||
  "http://127.0.0.1:5000/graphql";

const TOKEN_STORAGE_KEY = "ai_model_react_access";
const REFRESH_STORAGE_KEY = "ai_model_react_refresh";

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setAuthTokens(access: string, refresh?: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, access);
  if (refresh) {
    localStorage.setItem(REFRESH_STORAGE_KEY, refresh);
  }
}

export function clearAuthTokens(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  localStorage.removeItem(REFRESH_STORAGE_KEY);
}

export const djangoHttp = axios.create({
  baseURL: DJANGO_API_URL,
  timeout: 90000,
  headers: { "Content-Type": "application/json" },
});

export const fastApiHttp = axios.create({
  baseURL: FASTAPI_URL,
  timeout: 90000,
  headers: { "Content-Type": "application/json" },
});

export const postgraphqlHttp = axios.create({
  baseURL: POSTGRAPHQL_URL,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

function attachBearerToken(config: InternalAxiosRequestConfig): InternalAxiosRequestConfig {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}

djangoHttp.interceptors.request.use(attachBearerToken);
postgraphqlHttp.interceptors.request.use(attachBearerToken);

export interface GraphQLResponse<TData> {
  data?: TData;
  errors?: Array<{ message: string }>;
}

/** Execute a GraphQL query or mutation against the configured PostGraphQL endpoint. */
export async function executePostGraphQL<
  TData,
  TVariables extends Record<string, unknown> = Record<string, unknown>,
>(query: string, variables?: TVariables): Promise<TData> {
  const { data: payload } = await postgraphqlHttp.post<GraphQLResponse<TData>>("", {
    query,
    variables,
  });
  if (payload.errors?.length) {
    throw new Error(payload.errors.map((err) => err.message).join("; "));
  }
  if (payload.data === undefined) {
    throw new Error("PostGraphQL response did not include data.");
  }
  return payload.data;
}

export function extractErrorMessage(err: unknown): string {
  if (err instanceof AxiosError) {
    if (err.code === "ECONNABORTED") {
      return "Request timed out — the AI engine took longer than expected. Check that services are running or retry.";
    }
    const data = err.response?.data as Record<string, unknown> | undefined;
    if (data?.detail && typeof data.detail === "string") {
      return data.detail;
    }
    if (data && typeof data === "object") {
      return JSON.stringify(data);
    }
    return err.message;
  }
  return err instanceof Error ? err.message : "Unexpected network error";
}

export { DJANGO_API_URL, FASTAPI_URL, POSTGRAPHQL_URL };

