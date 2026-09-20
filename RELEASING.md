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
