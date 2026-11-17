/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DJANGO_API_URL?: string;
  readonly VITE_FASTAPI_URL?: string;
  readonly VITE_POSTGRAPHQL_URL?: string;
  readonly VITE_GRAPHQL_URL?: string;
  readonly VITE_APP_NAME?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

