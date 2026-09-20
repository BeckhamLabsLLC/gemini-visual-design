# Eval suite

Everything else in this repo checks that the tools *work when called*. This
checks whether Claude reaches for them at the right moment, which is a
different question and the one that decides whether the plugin is useful.

```bash
# See what would run, and roughly what it costs
claude plugin eval . --runs 1 --ablation none --no-publish

# The real thing: every case, against a no-plugin baseline
claude plugin eval . --concurrency 3 --max-cost-usd 10
```

Each run is a full Claude child session on your own credential, so the suite
costs real tokens — roughly **$0.13 per run**, and the default is 3 runs per
case per arm. Two arms × 5 cases × 3 runs is about **$4**. Use `--runs 1` while
iterating.

## What each case measures

| Case | The claim it tests |
|---|---|
| `mockup-invokes-plugin` | A mockup request produces an image, not hand-written HTML |
| `edit-over-regenerate` | A refinement edits the existing asset instead of regenerating — the plugin's central documented convention |
| `critique-uses-analyzer` | A critique request runs `analyze_design` and the runnable edit instructions reach the user, rather than generic design advice |
| `tier-matches-intent` | "Keep it cheap" does not get billed at the `pro` tier |
| `profile-before-generating` | "Make it match our look" establishes a style profile before generating |

## No API calls

`evals/mocks/gemini-visual-design/` stands in for the MCP server, so the suite
never reaches Google and never spends image-generation money. `_tools.json` is a
real `tools/list` response, so mocked tools carry their true schemas and
descriptions rather than a permissive placeholder — which matters, because the
descriptions are part of what steers the model.

Regenerate `_tools.json` after changing any tool schema:

```bash
python scripts/check_protocol.py   # confirms the server still answers
# then re-dump tools/list; see git history for the one-off script
```

The `expect:` blocks in each mock are assertions, not decoration: a call that
violates one aborts the run with score 0 and reports why. That is how a case
asserts what the plugin *asked the server to do*, not just that it called
something.

## Gotcha: tool names are namespaced differently here

Inside an eval sandbox the plugin's MCP tools are named

```
mcp__plugin_gemini-visual-design_gemini-visual-design__<tool>
```

not the `mcp__gemini-visual-design__<tool>` you see in an ordinary session. A
`tool_used` grader with the short name silently reports "called 0x" and the case
fails for the wrong reason. If every tool grader starts failing at once, check
this first.

## Reading the results

`results/<timestamp>/report.html` is self-contained — scores, prompts, and each
grader's verdict. `aggregate-result.json` has the same data for CI.

Graders marked `arm: with-only` are plugin-fired indicators: they are excluded
from the baseline arm's score, because "did it call an MCP tool the baseline
doesn't have" is not a fair thing to score the baseline on. The interesting
number is the **delta** between arms on the graders that both arms can satisfy —
that is what the plugin contributes over Claude working unaided.

`results/` is gitignored.
