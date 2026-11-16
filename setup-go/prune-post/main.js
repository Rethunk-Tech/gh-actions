const fs = require("fs");

// Post runs in a fresh process; persist the cache path from this step's env.
const cache = process.env.SETUP_GO_BUILD_CACHE || "";
fs.appendFileSync(process.env.GITHUB_STATE, `SETUP_GO_BUILD_CACHE=${cache}\n`);
