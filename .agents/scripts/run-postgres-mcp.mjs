#!/usr/bin/env node
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

// Resolve database URL from environment or .env file (never hardcode in config)
let dbUrl = process.env.DATABASE_URL || process.env.POSTGRES_URL;

if (!dbUrl) {
  const envPath = path.resolve(process.cwd(), ".env");
  if (fs.existsSync(envPath)) {
    const envContent = fs.readFileSync(envPath, "utf8");
    const match = envContent.match(/^DATABASE_URL=(.+)$/m);
    if (match) {
      dbUrl = match[1].trim();
    }
  }
}

if (!dbUrl) {
  // Default to standard local docker/postgres dev connection
  dbUrl = "postgresql://postgres:postgres@localhost:5432/smart_inventory";
}

// Normalize asyncpg / SQLAlchemy connection strings to standard postgresql://
if (dbUrl.startsWith("postgresql+asyncpg://")) {
  dbUrl = dbUrl.replace("postgresql+asyncpg://", "postgresql://");
} else if (dbUrl.startsWith("postgresql+psycopg://")) {
  dbUrl = dbUrl.replace("postgresql+psycopg://", "postgresql://");
}

// Launch official PostgreSQL MCP server with stdio transport
const child = spawn("npx", ["-y", "@modelcontextprotocol/server-postgres", dbUrl], {
  stdio: "inherit",
  shell: process.platform === "win32",
  env: {
    ...process.env,
    NODE_OPTIONS: [process.env.NODE_OPTIONS || "", "--no-deprecation"].filter(Boolean).join(" "),
  },
});

child.on("exit", (code) => {
  process.exit(code ?? 0);
});
