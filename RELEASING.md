# Releasing

There is no release automation on purpose — one maintainer, low release
cadence, and CI already guards the things that actually break.

1. **Reconcile `CHANGELOG.md`.** Move `[Unreleased]` to the new version with
   today's date, and add a link reference at the bottom. Every entry should
   say what broke for a user, not what changed in the code.

2. **Bump the version in all four places.** CI fails if they disagree:
   - `.claude-plugin/plugin.json`
   - `.claude-plugin/marketplace.json` (twice — top level and the plugin entry)
   - `pyproject.toml`
   - `src/gemini_visual_mcp/__init__.py`

3. **Run the gates locally.**
   ```bash
   pytest tests/ -q
   ruff check src/ tests/ && ruff format --check src/ tests/
   claude plugin validate .
   ```

4. **Run the protocol check.** Free, no API calls. The unit tests patch mcp's
   `Server`, so they cannot see a broken launch command, an unresolvable
   dependency, or an unregistered handler.
   ```bash
   python scripts/check_protocol.py
   ```

5. **Run the live smoke test** if anything touched a model id, the client, or
   generation. Mocks cannot tell you a model was retired.
   ```bash
   python scripts/smoke_live.py --dry-run   # see the cost first
   python scripts/smoke_live.py             # ~$0.80
   ```

6. **Tag and release.**
   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z
   gh release create vX.Y.Z --title "vX.Y.Z — <one line>" --notes-file <changelog section>
   ```

7. **Verify the install path** from a clean machine or container:
   ```
   /plugin install gemini-visual-design --marketplace BeckhamLabsLLC/gemini-visual-design
   ```

## Model IDs

Google retires models on its own schedule, and a retired id fails at runtime
with no warning at build time — this is what broke v1.0.0. `tests/test_model_ids.py`
fails if a configured id is a `-preview` build or is hardcoded outside
`config.py`, but it cannot know what Google retired yesterday. Before a
release, check the
[deprecations page](https://ai.google.dev/gemini-api/docs/deprecations) and run
check 0 of the smoke test, which lists every configured id against the live API:

```bash
python scripts/smoke_live.py --only models_list   # free
```

## Community marketplace

The plugin is not yet listed in `anthropics/claude-plugins-community`. Submitting
puts it in the `/plugin` Discover tab, which is the only in-product distribution
channel there is.

Submission is an in-app form, not a pull request — PRs opened against that repo
are closed automatically:

- **Console** (individual authors): [platform.claude.com/plugins/submit](https://platform.claude.com/plugins/submit)
- **claude.ai** (Team/Enterprise orgs with directory access): [claude.ai/admin-settings/directory/submissions/plugins/new](https://claude.ai/admin-settings/directory/submissions/plugins/new)

The review pipeline runs `claude plugin validate` plus automated safety
screening. Run it first:

```bash
claude plugin validate . --strict
```

Approved plugins are pinned to a commit SHA, CI bumps the pin as you push, and
the public catalog syncs nightly — so expect a delay between approval and the
plugin appearing in
[the catalog's marketplace.json](https://github.com/anthropics/claude-plugins-community/blob/main/.claude-plugin/marketplace.json).

## Measuring whether the plugin actually helps

The test suite proves the tools work when called. `evals/` checks whether Claude
reaches for them at the right moment, which is the question that decides whether
the plugin is worth installing.

```bash
claude plugin eval . --concurrency 3 --max-cost-usd 10
```

It runs each case with and without the plugin loaded and reports the delta. Runs
are real Claude child sessions on your credential — about $0.13 each, so a full
two-arm pass over five cases at the default 3 runs is roughly $4. The MCP server
is mocked, so no Gemini API money is spent.

Worth running before a release and whenever a new model ships: a model change
can silently stop Claude reaching for a tool without breaking a single unit
test. See `evals/README.md` for what each case asserts.

This is deliberately not in CI — it needs a credential and costs money per run.
