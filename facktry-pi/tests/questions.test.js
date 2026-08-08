import assert from "node:assert/strict";
import test from "node:test";

const question = {
  id: "autonomy",
  prompt: "How much autonomy is acceptable?",
  options: [
    { value: "bounded", label: "Bounded", description: "Pause at irreversible steps." },
    { value: "supervised", label: "Supervised" },
  ],
};

const load = () => import("../src/tools/questions.js");

test("questions normalization supplies documented defaults", async () => {
  const { normalizeQuestions } = await load();
  const [normalized] = normalizeQuestions([question]);
  assert.equal(normalized.label, "Q1");
  assert.equal(normalized.allowOther, true);
  assert.equal(normalized.allowDetail, true);
  assert.equal(normalized.detailPrompt, "Add detail (optional)");
  assert.equal(normalized.required, true);
});

test("questions normalization rejects empty questions, options, and duplicate ids", async () => {
  const { QuestionValidationError, normalizeQuestions } = await load();
  for (const invalid of [[], [{ ...question, options: [] }], [question, { ...question }]]) {
    assert.throws(() => normalizeQuestions(invalid), QuestionValidationError);
  }
});

test("answer transitions preserve selection, detail-clearing, and custom-answer semantics", async () => {
  const { applyAnswerTransition, normalizeQuestions } = await load();
  const [normalized] = normalizeQuestions([question]);
  let answer = applyAnswerTransition(null, normalized, { kind: "select", value: "bounded" });
  assert.deepEqual(answer, { question_id: "autonomy", value: "bounded", label: "Bounded", detail: null, was_custom: false });
  answer = applyAnswerTransition(answer, normalized, { kind: "detail", detail: "Require human promotion." });
  assert.equal(answer.detail, "Require human promotion.");
  answer = applyAnswerTransition(answer, normalized, { kind: "select", value: "supervised" });
  assert.equal(answer.value, "supervised");
  assert.equal(answer.detail, null);
  answer = applyAnswerTransition(answer, normalized, { kind: "custom", value: "review every run" });
  assert.deepEqual(answer, { question_id: "autonomy", value: "review every run", label: "review every run", detail: null, was_custom: true });
});

test("cancelled questionnaire result has no answers and formatters retain prompt label and detail", async () => {
  const { cancelledQuestionResult, formatQuestionContent, renderQuestionResult } = await load();
  const cancelled = cancelledQuestionResult();
  assert.deepEqual(cancelled, { cancelled: true, answers: [] });
  const result = {
    cancelled: false,
    answers: [{ question_id: "autonomy", value: "bounded", label: "Bounded", detail: "Pause at promotion.", was_custom: false }],
  };
  assert.match(formatQuestionContent(result, [question]), /How much autonomy/);
  assert.match(formatQuestionContent(result, [question]), /Pause at promotion/);
  assert.match(renderQuestionResult(result, [question]), /Bounded/);
});

test("questions tool registers sequentially and refuses headless human interaction without throwing", async () => {
  const { createQuestionsTool } = await load();
  const tool = createQuestionsTool();
  assert.equal(tool.name, "questions");
  assert.equal(tool.executionMode, "sequential");
  const result = await tool.execute({ ui: { mode: "print" } }, { questions: [question] });
  assert.equal(result.details.ok, false);
  assert.equal(result.details.reason, "tui_required");
  assert.match(result.content[0].text, /tui/i);
});
