const { spawnSync } = require("child_process");
const path = require("path");

const cache =
	process.env.STATE_SETUP_GO_BUILD_CACHE ||
	process.env.SETUP_GO_BUILD_CACHE ||
	"";
const script = path.join(__dirname, "..", "prune-build-cache.sh");
const result = spawnSync("bash", [script, cache], { stdio: "inherit" });
process.exit(result.status === null ? 1 : result.status);
