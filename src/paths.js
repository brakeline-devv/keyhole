// Where Keyhole keeps its cache and watchlist.
// From a git checkout: ./data next to the code. Installed from npm (npx / global): ~/.keyhole.
// KEYHOLE_HOME overrides both.
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import { fileURLToPath } from "node:url";

const pkgDir = fileURLToPath(new URL("..", import.meta.url));
const installed = pkgDir.split(/[\\/]/).some((part) => part === "node_modules" || part === "_npx");
export const DATA_DIR = process.env.KEYHOLE_HOME || (installed ? join(homedir(), ".keyhole") : join(pkgDir, "data"));
mkdirSync(join(DATA_DIR, "cache"), { recursive: true });
export const dataFile = (name) => join(DATA_DIR, name);
export const cacheFile = (name) => join(DATA_DIR, "cache", name);
