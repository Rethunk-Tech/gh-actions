import { expect, test } from "bun:test";
import { annotation, classify, latestVersion, type Report } from "./audit.ts";

const advisory = (vulnerable_versions: string) => ({
	id: 1,
	url: "https://github.com/advisories/GHSA-x",
	title: "t",
	severity: "high",
	vulnerable_versions,
});

test("an advisory whose range excludes the latest release is fixable", () => {
	const report: Report = { lodash: [advisory("<4.17.21")] };
	const { fixable, unfixable } = classify(report, { lodash: "4.17.21" });
	expect(fixable.map((f) => f.pkg)).toEqual(["lodash"]);
	expect(unfixable).toEqual([]);
});

test("an advisory that still covers the latest release has no patch and only warns", () => {
	const report: Report = { oldlib: [advisory(">=1.0.0 <=2.3.0")] };
	const { fixable, unfixable } = classify(report, { oldlib: "2.3.0" });
	expect(fixable).toEqual([]);
	expect(unfixable.map((f) => f.pkg)).toEqual(["oldlib"]);
});

test("one package can split across both paths", () => {
	const report: Report = { p: [advisory("<1.0.1"), advisory("*")] };
	const { fixable, unfixable } = classify(report, { p: "1.0.1" });
	expect(fixable).toHaveLength(1);
	expect(unfixable).toHaveLength(1);
});

test("an unknown latest version fails closed", () => {
	const { fixable } = classify({ p: [advisory("*")] }, { p: undefined });
	expect(fixable).toHaveLength(1);
});

test("annotations encode newlines", () => {
	expect(annotation("warning", "a\nb%")).toBe("::warning::a%0Ab%25");
});

test("a non-array advisories value is rejected", () => {
	expect(() =>
		classify({ p: { id: 1 } } as unknown as Report, { p: "1.0.0" }),
	).toThrow(/not an advisory list/);
});

test("a malformed advisory is rejected", () => {
	expect(() =>
		classify({ p: [null] } as unknown as Report, { p: "1.0.0" }),
	).toThrow(/malformed advisory/);
});

test("registry URLs encode every slash so a name cannot walk the path", async () => {
	const orig = globalThis.fetch;
	const urls: string[] = [];
	globalThis.fetch = (async (input) => {
		urls.push(String(input));
		return new Response(JSON.stringify({ version: "1.0.0" }));
	}) as typeof fetch;
	try {
		await latestVersion("foo/bar/baz");
		await latestVersion("@scope/name");
		expect(urls).toEqual([
			"https://registry.npmjs.org/foo%2Fbar%2Fbaz/latest",
			"https://registry.npmjs.org/@scope%2Fname/latest",
		]);
	} finally {
		globalThis.fetch = orig;
	}
});

test("registry fetch passes an abort signal", async () => {
	const orig = globalThis.fetch;
	let sawSignal = false;
	globalThis.fetch = (async (_input, init) => {
		sawSignal = init?.signal != null;
		return new Response(JSON.stringify({ version: "1.0.0" }));
	}) as typeof fetch;
	try {
		expect(await latestVersion("lodash")).toBe("1.0.0");
		expect(sawSignal).toBe(true);
	} finally {
		globalThis.fetch = orig;
	}
});

test("a thrown registry fetch counts as unknown latest", async () => {
	const orig = globalThis.fetch;
	globalThis.fetch = (async () => {
		throw new Error("network");
	}) as typeof fetch;
	try {
		expect(await latestVersion("lodash")).toBeUndefined();
	} finally {
		globalThis.fetch = orig;
	}
});
