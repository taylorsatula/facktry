import assert from "node:assert/strict";
import test from "node:test";

const papers = () => import("../src/tools/papers.js");
const research = () => import("../src/tools/research.js");

const html = `
  <html><body>
    <h1>Grounded tool use</h1><p>Abstract text.</p>
    <h2>3 Evaluation</h2><p>Paired sealed evaluation is required.</p>
  </body></html>
`;

test("papers extracts sections and supports number or fuzzy-title selection", async () => {
  const { extractPaperSections, selectPaperSection } = await papers();
  const sections = extractPaperSections(html);
  assert.match(selectPaperSection(sections, "3").text, /Paired sealed/);
  assert.match(selectPaperSection(sections, "evaluation").text, /Paired sealed/);
});

test("papers retrieval preserves identifiers, direction, cache, and fallback", async () => {
  const { PaperCache, formatPaperSearchResults, fetchCitationGraph, paperTextOrAbstract } = await papers();
  assert.match(formatPaperSearchResults([{ arxiv_id: "2401.01234", title: "Tool use" }]), /2401\.01234/);

  const calls = [];
  const client = { get: async (path) => { calls.push(path); return { data: [] }; } };
  await fetchCitationGraph(client, "2401.01234", { direction: "references" });
  await fetchCitationGraph(client, "2401.01234", { direction: "citations" });
  assert.deepEqual(calls, ["/paper/2401.01234/references", "/paper/2401.01234/citations"]);

  const cache = new PaperCache();
  let fetches = 0;
  assert.equal(await cache.getOrFetch("2401.01234", async () => { fetches += 1; return "cached"; }), "cached");
  assert.equal(await cache.getOrFetch("2401.01234", async () => { fetches += 1; return "refetched"; }), "cached");
  assert.equal(fetches, 1);
  assert.equal(paperTextOrAbstract("", "abstract fallback"), "abstract fallback");
});

test("research worker enforces its allowlist and loop-output safeguards", async () => {
  const { assertResearchToolAllowed, detectDoomLoop, truncateToolOutput } = await research();
  assert.throws(() => assertResearchToolAllowed("train_smoke"), /allowlist/i);
  assert.throws(() => assertResearchToolAllowed("write"), /allowlist/i);
  assert.equal(assertResearchToolAllowed("papers_search"), true);
  assert.equal(truncateToolOutput("x".repeat(120), 32), "x".repeat(32));
  assert.equal(detectDoomLoop(["papers_search:q", "papers_search:q", "papers_search:q"]), true);
});

test("research integration returns one bounded summary and unique parallel call ids", async () => {
  const { createResearchTool, uniqueToolCallId } = await research();
  const first = uniqueToolCallId("papers_search");
  const second = uniqueToolCallId("papers_search");
  assert.notEqual(first, second);

  const tool = createResearchTool({
    runWorker: async () => ({ summary: "Use paired sealed measurement.", references: ["arxiv:2401.01234"] }),
  });
  const result = await tool.execute({ ui: { mode: "print" } }, { query: "tool-use SFT" });
  assert.equal(result.details.ok, true);
  assert.match(result.content[0].text, /paired sealed/i);
  assert.equal(result.content.length, 1);
});

test("research loop summarizes at the iteration cap and aborts without leaving worker state", async () => {
  const { runResearchLoop } = await research();
  const capped = await runResearchLoop({
    maxIterations: 2,
    next: async () => ({ tool: "papers_search", input: { query: "grounding" } }),
    callTool: async () => "result",
  });
  assert.equal(capped.reason, "max_iterations");
  assert.ok(capped.summary);

  const controller = new AbortController();
  controller.abort();
  const aborted = await runResearchLoop({ signal: controller.signal, next: async () => null, callTool: async () => "unused" });
  assert.equal(aborted.reason, "aborted");
  assert.equal(aborted.worker_active, false);
});
