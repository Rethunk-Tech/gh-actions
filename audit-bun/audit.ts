// Fails only on advisories whose fix has shipped; the rest warn with the dependency chain.

export interface Advisory {
	id: number;
	url: string;
	title: string;
	severity: string;
	vulnerable_versions: string;
}

/** `bun audit --json`: advisories by package name. */
export type Report = Record<string, Advisory[]>;

export interface Finding {
	pkg: string;
	advisory: Advisory;
	latest: string | undefined;
}

/**
 * An advisory is fixable when the package's latest published version falls outside its
 * vulnerable range. A package whose latest version is unknown counts as fixable: failing
 * closed beats passing an advisory because the registry was unreachable.
 */
export function classify(
	report: Report,
	latest: Record<string, string | undefined>,
): { fixable: Finding[]; unfixable: Finding[] } {
	const fixable: Finding[] = [];
	const unfixable: Finding[] = [];
	for (const [pkg, advisories] of Object.entries(report)) {
		if (!Array.isArray(advisories)) {
			throw new TypeError(
				`bun audit JSON for ${JSON.stringify(pkg)} is not an advisory list`,
			);
		}
		const version = latest[pkg];
		for (const advisory of advisories) {
			if (
				advisory === null ||
				typeof advisory !== "object" ||
				typeof advisory.vulnerable_versions !== "string"
			) {
				throw new TypeError(
					`bun audit JSON for ${JSON.stringify(pkg)} has a malformed advisory`,
				);
			}
			const finding = { pkg, advisory, latest: version };
			const stillVulnerable =
				version !== undefined &&
				Bun.semver.satisfies(version, advisory.vulnerable_versions);
			(stillVulnerable ? unfixable : fixable).push(finding);
		}
	}
	return { fixable, unfixable };
}

/** Workflow commands end at the first newline, so a multi-line message is percent-encoded. */
export const annotation = (
	level: "error" | "warning",
	message: string,
): string =>
	`::${level}::${message.replaceAll("%", "%25").replaceAll("\r", "%0D").replaceAll("\n", "%0A")}`;

function registryLatestUrl(pkg: string): string {
	return `https://registry.npmjs.org/${pkg.replaceAll("/", "%2F")}/latest`;
}

export async function latestVersion(pkg: string): Promise<string | undefined> {
	try {
		const res = await fetch(registryLatestUrl(pkg), {
			signal: AbortSignal.timeout(10_000),
		});
		if (!res.ok) {
			return undefined;
		}
		return ((await res.json()) as { version?: string }).version;
	} catch {
		return undefined;
	}
}

async function why(pkg: string): Promise<string> {
	const proc = Bun.spawn(["bun", "why", pkg], {
		stdout: "pipe",
		stderr: "pipe",
		timeout: 30_000,
	});
	const out = await new Response(proc.stdout).text();
	await proc.exited;
	return out.trim();
}

async function main(): Promise<number> {
	const proc = Bun.spawn(["bun", "audit", "--json"], {
		stdout: "pipe",
		stderr: "inherit",
		timeout: 120_000,
	});
	const raw = await new Response(proc.stdout).text();
	await proc.exited;
	let report: Report;
	try {
		report = JSON.parse(raw) as Report;
	} catch {
		console.log(
			annotation("error", `bun audit did not print JSON: ${raw.slice(0, 500)}`),
		);
		return 1;
	}
	const names = Object.keys(report);
	const versions = await Promise.all(names.map((n) => latestVersion(n)));
	const latest = Object.fromEntries(names.map((n, i) => [n, versions[i]]));
	const { fixable, unfixable } = classify(report, latest);

	for (const f of unfixable) {
		const chain = await why(f.pkg);
		console.log(
			annotation(
				"warning",
				`${f.pkg} ${f.advisory.severity}: ${f.advisory.title} (${f.advisory.url}); no patched release (latest ${f.latest}).\n${chain}`,
			),
		);
	}
	for (const f of fixable) {
		console.log(
			annotation(
				"error",
				`${f.pkg} ${f.advisory.severity}: ${f.advisory.title} (${f.advisory.url}); vulnerable ${f.advisory.vulnerable_versions}, latest ${f.latest ?? "unknown"}.`,
			),
		);
	}
	console.log(
		`bun audit: ${fixable.length} fixable, ${unfixable.length} without a patched release`,
	);
	return fixable.length > 0 ? 1 : 0;
}

if (import.meta.main) {
	try {
		process.exit(await main());
	} catch (err) {
		const message = err instanceof Error ? err.message : String(err);
		console.log(annotation("error", message));
		process.exit(1);
	}
}
