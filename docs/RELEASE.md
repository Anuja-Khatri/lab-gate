# Releasing lab-gate 1.0.0 to PyPI

A checklist for the owner. Plain language, copy-paste commands. Nothing in this
repository uploads anything by itself: every upload below happens only when you do it.

**Read this first.** PyPI never lets the same version number be uploaded twice, even
after a delete. If something is wrong after upload, the fix is a new version (1.0.1).
So do the checks in steps 1 and 2 before step 4.

The name `lab-gate` was free on PyPI on 16 Nov 2026. To check again, open
https://pypi.org/project/lab-gate/ . "Not Found" means it is still free.

---

## Step 0. Get the release onto `main`

The package should be built from `main`, so that the links on the PyPI page (which
point to files on `main`) work.

1. On GitHub, open a pull request from the branch `wp2-release` into `main`.
2. Read it, then merge it.

## Step 1. Build and check on your computer (about 5 minutes)

You need Python 3.12 or newer. Check with:

```
python3 --version
```

Then, in a terminal:

```
git clone https://github.com/Anuja-Khatri/lab-gate.git lab-gate-release
cd lab-gate-release
bash scripts/check_release.sh
```

(If your `python3` is older than 3.12 but you have `python3.12`, run
`PYTHON=python3.12 bash scripts/check_release.sh` instead.)

That one script does everything below and stops with `FAIL` if anything is wrong:

- builds the two files that get uploaded into `dist/`:
  `lab_gate-1.0.0.tar.gz` and `lab_gate-1.0.0-py3-none-any.whl`;
- runs `twine check --strict` on them (checks the PyPI page will render);
- makes a brand-new, empty Python environment, installs only the wheel, and runs the
  README quickstart there: the three example plans must give PASS (exit 0), BLOCK
  (exit 1) and ABSTAIN (exit 2), `--json` must work, and the README's Python example
  must print exactly what the README says.

The last line must be:

```
== release check passed: dist/ is ready (nothing was uploaded)
```

If you prefer to run the steps by hand, they are:

```
python3 -m venv /tmp/lg-build && /tmp/lg-build/bin/pip install build twine
rm -rf dist && /tmp/lg-build/bin/python -m build
/tmp/lg-build/bin/twine check --strict dist/*

python3 -m venv /tmp/lg-test && /tmp/lg-test/bin/pip install dist/lab_gate-1.0.0-py3-none-any.whl
mkdir /tmp/lg-try && cd /tmp/lg-try
/tmp/lg-test/bin/lab-gate examples .
/tmp/lg-test/bin/lab-gate check plan_pass.json    --rules rules.yaml; echo "exit $?"   # PASS, exit 0
/tmp/lg-test/bin/lab-gate check plan_block.json   --rules rules.yaml; echo "exit $?"   # BLOCK, exit 1
/tmp/lg-test/bin/lab-gate check plan_abstain.json --rules rules.yaml; echo "exit $?"   # ABSTAIN, exit 2
```

## Step 2. One-time setup for trusted publishing (recommended)

Trusted publishing lets GitHub upload the package for you without any password or
token stored anywhere. You set it up once.

**On pypi.org** (create an account first if needed; PyPI requires two-factor login):

1. Log in at https://pypi.org .
2. Click your user name (top right), then **Your projects**, then **Publishing** in
   the left menu. (Direct link: https://pypi.org/manage/account/publishing/ )
3. Under **Add a new pending publisher**, choose the **GitHub** tab and fill in:
   - PyPI Project Name: `lab-gate`
   - Owner: `Anuja-Khatri`
   - Repository name: `lab-gate`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`
4. Click **Add**.

**On github.com**:

1. Open https://github.com/Anuja-Khatri/lab-gate , then **Settings**, then
   **Environments**, then **New environment**.
2. Name it `pypi` (exactly) and click **Configure environment**.
3. Recommended: tick **Required reviewers**, add yourself, and click
   **Save protection rules**. Then every upload waits for your click.

Optional rehearsal on TestPyPI (a separate practice site): make an account at
https://test.pypi.org , add the same pending publisher there but with Environment
name `testpypi`, and create a GitHub environment called `testpypi`. Then in GitHub
open **Actions**, then **publish**, then **Run workflow**, choose `testpypi`, and run
it. It uploads to https://test.pypi.org/project/lab-gate/ only.

## Step 3. Look at the workflow before you use it

The workflow file is `.github/workflows/publish.yml`. It runs only when you publish a
GitHub Release, or when you click **Run workflow** yourself. It never runs on a push.
Before uploading, it runs the same `scripts/check_release.sh` as step 1, and on a
release it checks that the release tag matches the version `1.0.0`.

## Step 4. Publish

1. On GitHub, open **Releases** (right-hand side of the repository page), then
   **Draft a new release**.
2. **Choose a tag**: type `v1.0.0` and click **Create new tag: v1.0.0 on publish**.
   Target: `main`.
3. Release title: `lab-gate 1.0.0`. Description: paste the 1.0.0 section of
   `CHANGELOG.md`.
4. Click **Publish release**.
5. Open the **Actions** tab. The `publish` run builds and checks the package. If you
   set required reviewers, click **Review deployments**, tick `pypi`, and approve.
6. When it is green, the package is at https://pypi.org/project/lab-gate/ .

Do not move or delete the existing tag `prereg-v1`; it is the preregistration
timestamp.

### Alternative: upload by hand with twine

Only if you do not want trusted publishing.

1. On pypi.org: your user name, then **Account settings**, then **API tokens**, then
   **Add API token**. Scope: "Entire account" for the first upload (you can make a
   project-only token afterwards). Copy the token (it starts with `pypi-`). It is shown
   once. Do not paste it into any file in the repository.
2. From the folder where step 1 built `dist/`:

   ```
   /tmp/lg-build/bin/twine upload dist/*
   ```

   (If you used `scripts/check_release.sh`, first run
   `python3 -m venv /tmp/lg-build && /tmp/lg-build/bin/pip install twine`.)
   When asked for the username type `__token__`; for the password paste the token.
3. Delete the token on pypi.org afterwards if you will not use it again.

## Step 5. Check the published package

In a new terminal, in an empty folder:

```
python3 -m venv /tmp/lg-pypi && /tmp/lg-pypi/bin/pip install lab-gate
/tmp/lg-pypi/bin/lab-gate version            # lab-gate 1.0.0
/tmp/lg-pypi/bin/lab-gate examples .
/tmp/lg-pypi/bin/lab-gate check plan_block.json --rules rules.yaml   # BLOCK
```

Then update `CHANGELOG.md` on `main`: change `## [1.0.0] - unreleased` to today's
date.
