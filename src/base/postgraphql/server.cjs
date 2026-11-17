"use strict";

const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { postgraphile } = require("postgraphile");

const backendEnvPath = path.resolve(__dirname, "../../backend/.env");
if (fs.existsSync(backendEnvPath) && typeof process.loadEnvFile === "function") {
  process.loadEnvFile(backendEnvPath);
}

function buildDatabaseUrl() {
  const socketDir = path.resolve(__dirname, "../.run");
  const socketFile = path.join(socketDir, ".s.PGSQL.5433");
  const user = encodeURIComponent(process.env.POSTGRES_USER || "ai_model");
  const password = encodeURIComponent(process.env.POSTGRES_PASSWORD || "ai_model_dev_pass");
  const database = encodeURIComponent(process.env.POSTGRES_DB || "ai_model");

  if (fs.existsSync(socketFile)) {
    return `postgresql://${user}:${password}@/${database}?host=${encodeURIComponent(socketDir)}&port=5433`;
  }
  if (process.env.DATABASE_URL) {
    return process.env.DATABASE_URL;
  }
  const host = process.env.POSTGRES_HOST || "127.0.0.1";
  const port = process.env.POSTGRES_PORT || "5433";
  return `postgresql://${user}:${password}@${host}:${port}/${database}`;
}

const databaseUrl = buildDatabaseUrl();
const host = process.env.POSTGRAPHILE_HOST || "127.0.0.1";
const port = Number(process.env.POSTGRAPHILE_PORT || 5000);
const schemas = (process.env.POSTGRAPHILE_SCHEMA || "public")
  .split(",")
  .map((item) => item.trim())
  .filter(Boolean);
const isDev = (process.env.DJANGO_DEBUG || "True").toLowerCase() === "true";

const middleware = postgraphile(databaseUrl, schemas, {
  watchPg: true,
  graphiql: true,
  enhanceGraphiql: true,
  enableCors: true,
  dynamicJson: true,
  ignoreRBAC: false,
  setofFunctionsContainNulls: false,
  graphqlRoute: "/graphql",
  graphiqlRoute: "/graphiql",
  showErrorStack: isDev ? "json" : false,
  extendedErrors: isDev ? ["hint", "detail", "errcode"] : ["errcode"],
});

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
  });
  res.end(JSON.stringify(payload));
}

function forwardGetQueryToPost(req, res, parsedUrl) {
  const query = parsedUrl.searchParams.get("query");
  const operationName = parsedUrl.searchParams.get("operationName") || undefined;
  let variables;
  const rawVars = parsedUrl.searchParams.get("variables");
  if (rawVars) {
    try {
      variables = JSON.parse(rawVars);
    } catch {
      sendJson(res, 400, { errors: [{ message: "Invalid JSON in 'variables' query parameter." }] });
      return;
    }
  }

  const body = JSON.stringify({ query, variables, operationName });
  const headers = {
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(body),
  };
  if (req.headers.authorization) {
    headers.Authorization = req.headers.authorization;
  }

  const proxyReq = http.request(
    { host, port, path: "/graphql", method: "POST", headers },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 200, proxyRes.headers);
      proxyRes.pipe(res);
    }
  );
  proxyReq.on("error", (err) => {
    sendJson(res, 502, { errors: [{ message: `GraphQL proxy error: ${err.message}` }] });
  });
  proxyReq.end(body);
}

const server = http.createServer((req, res) => {
  const parsedUrl = new URL(req.url || "/", `http://${host}:${port}`);

  if (parsedUrl.pathname === "/health") {
    sendJson(res, 200, {
      status: "ok",
      service: "postgraphile",
      schemas,
      graphql: "/graphql",
      graphiql: "/graphiql",
    });
    return;
  }

  if (req.method === "GET" && parsedUrl.pathname === "/graphql") {
    if (parsedUrl.searchParams.has("query")) {
      forwardGetQueryToPost(req, res, parsedUrl);
      return;
    }
    const accept = String(req.headers.accept || "");
    if (accept.includes("text/html")) {
      res.writeHead(302, { Location: "/graphiql" });
      res.end();
      return;
    }
    sendJson(res, 200, {
      status: "ok",
      service: "postgraphile",
      schemas,
      graphql: "/graphql",
      graphiql: "/graphiql",
      usage:
        'POST /graphql with {"query":"{ allBillingPlans { nodes { id name slug } } }"} or GET /graphql?query=...',
    });
    return;
  }

  middleware(req, res);
});

server.listen(port, host, () => {
  console.log(`PostGraphQL listening on http://${host}:${port}/graphql (GraphiQL: /graphiql)`);
});

function shutdown(signal) {
  console.log(`Received ${signal}, shutting down PostGraphQL...`);
  server.close(() => process.exit(0));
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
