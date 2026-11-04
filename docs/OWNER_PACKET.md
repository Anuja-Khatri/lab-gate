# Owner packet — exact remaining steps

Everything Claude Code can do is done, committed locally, and verified from a fresh
clone (`make setup && make ci && make sim && make demo`, all offline). The steps below
are yours (human-only: publishing, external accounts). They are copy-paste ready.
Replace `<you>` / `<...>` placeholders. Run from the repo root unless noted.

`$WS` is the parent directory that holds both `lab-gate/` and `helao-async/`.

---

## (a) Read in this order

1. **`docs/FINAL_REPORT.md`** — the whole study. Check the Section 2 headline table
   (typed gate 0.00 attack / 0.00 false-block; opus LLM gate permissive 0.28; gpt-5.1
   over-blocks 0.64) and Section 6 (deviations + the D-033 extension). Confirm you are
   comfortable with every reduced-n caveat before anything is published.
2. **`docs/CORRECTIONS.md`** — the one retraction. Check the old→new table: round-2's
   opus "over-abstention 0.90" was a truncation artifact; the corrected opus gate is
   permissive. Make sure you can explain this if asked, because it is the most
   important integrity point in the project.
3. **`DECISIONS.md`** — D-001..D-033, append-only. Skim for any decision you disagree
   with; D-022 (keys/spend), D-030 (the truncation fix), D-033 (the attacker extension)
   are the load-bearing ones.
4. **`docs/POST.md`** — the ~900-word public writeup. Check the tone and that every
   number matches the report. The optional citations are in an HTML comment at the end;
   add only links you verify yourself.

Also skim `docs/tables/results.md` (every number with n and 95% CI) and
`LIMITATIONS.md` (what the work does NOT claim).

---

## (b) GitHub

Suggested repo **name**: `lab-gate`

Suggested **description** (contains the discoverability terms):

> A plan-checking safety gate for autonomous labs, built on helao-async and evaluated in its OERSIM simulator. Returns PASS (proof certificate), BLOCK (counterexample), or ABSTAIN, reading only typed fields, never free text.

Suggested **topics**: `helao-async`, `oersim`, `autonomous-labs`, `self-driving-lab`,
`ai-safety`, `formal-methods`, `smt`, `z3`, `ltl`, `plan-checking`, `safety-gate`.

Push, after you create an EMPTY repo on GitHub (no README/license, so there is nothing
to merge):

```
cd $WS/lab-gate
git remote add origin git@github.com:<you>/lab-gate.git   # or the https URL
git push -u origin main
git push origin prereg-v1                                   # the binding prereg tag
```

Verify the tag landed: `git ls-remote --tags origin | grep prereg-v1`.

Do NOT commit `$WS/.env`; it is gitignored and was never tracked (secret scan is clean
on the working tree and the full history).

---

## (c) OSF preregistration

The preregistration is `docs/PREREGISTRATION.md`. Its binding timestamp is the git tag
**`prereg-v1`**, commit **`b06ae95d35bc985ebb0c3599b45dcedb4e4468af`**, dated
**2026-11-03 18:16:31 +0530**. The tag is an ancestor of `main`, so the held-out runs
provably came after it.

Steps:

1. Create an OSF account / project at https://osf.io (project title e.g.
   "lab-gate: a plan-checking safety gate for autonomous labs").
2. Under the project, create a **Registration** (or upload `docs/PREREGISTRATION.md` as
   a component file first, then register). Paste or attach `docs/PREREGISTRATION.md`.
3. In the registration narrative, include this disclosure line verbatim:

   > The binding timestamp of this preregistration is the public git tag `prereg-v1`
   > (commit `b06ae95d35bc985ebb0c3599b45dcedb4e4468af`) in the lab-gate repository; the
   > git tag, not the OSF upload date, is the authoritative pre-registration timestamp.

4. After you push to GitHub (step b), add the repo URL and the direct tag URL
   (`https://github.com/<you>/lab-gate/releases/tag/prereg-v1`) to the OSF registration
   so the timestamp is externally checkable.

---

## (d) Media rendering

Tools are not installable in the build environment (R-02), so these are yours. The
real asciinema cast is already committed at `media/demo.cast`.

GIF from the cast (install `agg` first — `brew install agg`, or `cargo install --git
https://github.com/asciinema/agg`):

```
agg media/demo.cast media/demo.gif
```

Site walkthrough webm (needs Playwright with Chromium):

```
cd $WS/lab-gate
python -m pip install playwright && python -m playwright install chromium
# then record site/index.html with any screen recorder, OR a short script:
python - <<'PY'
from playwright.sync_api import sync_playwright
import pathlib
url = pathlib.Path("site/index.html").resolve().as_uri()
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(record_video_dir="media/", viewport={"width":1280,"height":800})
    pg.goto(url)
    for y in range(0, 4000, 200):
        pg.mouse.wheel(0, 200); pg.wait_for_timeout(300)
    pg.wait_for_timeout(1000); b.close()
PY
# Playwright writes a .webm into media/; rename it:
mv media/*.webm media/site-walkthrough.webm
```

Keep the webm under 2 minutes.

---

## (e) arXiv

An arXiv-ready PDF is already produced and committed at **`docs/FINAL_REPORT.pdf`**
(generated from `docs/FINAL_REPORT.md` with pandoc 3.9 + pdflatex). You can upload that
PDF directly.

To regenerate it (pandoc installs into the venv with no system change):

```
cd $WS/lab-gate
uv pip install --python .venv/bin/python pypandoc-binary
.venv/bin/python - <<'PY'
import pypandoc
pypandoc.convert_file("docs/FINAL_REPORT.md", "pdf", format="gfm",
    outputfile="docs/FINAL_REPORT.pdf",
    extra_args=["--pdf-engine=pdflatex","-V","geometry:margin=1in",
                "-V","colorlinks=true","--toc",
                "-V","title=lab-gate: a plan-checking safety gate for autonomous labs"])
print("wrote docs/FINAL_REPORT.pdf")
PY
```

Before submission: verify the Guevarra et al. OER venue/year and the HELAO orchestration
paper citation in the report (the DOI lineage is noted in the References section). arXiv
accepts a PDF-only submission; if a moderator asks for source, the markdown is
`docs/FINAL_REPORT.md`.

---

## Out of scope (by owner instruction)

No outreach messages, issues, or emails were drafted. The notes to collaborators are to
be written with you after you have reviewed the real numbers.
