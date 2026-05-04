/**
 * Export backend OpenAPI JSON into src/generated/openapi.json using the backend
 * service image and Docker Compose (see docs/tech/docker-dev.md).
 */
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendRoot, "../..");
const outDir = path.join(frontendRoot, "src", "generated");
const composeFile = path.join(repoRoot, "docker-compose.yml");
const envFile = path.join(repoRoot, ".env.development");

if (!fs.existsSync(envFile)) {
  console.error(
    "Missing .env.development at repo root. Copy .env.development.example first.",
  );
  process.exit(1);
}

fs.mkdirSync(outDir, { recursive: true });

const volumeMount =
  process.platform === "win32"
    ? `${outDir.replace(/\\/g, "/")}:/out`
    : `${outDir}:/out`;

const args = [
  "compose",
  "-f",
  composeFile,
  "--env-file",
  envFile,
  "run",
  "--rm",
  "--no-deps",
  "-v",
  volumeMount,
  "backend",
  "uv",
  "run",
  "python",
  "-m",
  "app.export_openapi",
  "--output",
  "/out/openapi.json",
];

execFileSync("docker", args, { stdio: "inherit", cwd: repoRoot });
