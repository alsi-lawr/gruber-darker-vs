# Contributing

This extension's `.vstheme` is generated, not hand-edited. Read this before changing colours.

## Layout

| Path | Role |
| --- | --- |
| `source.vstheme` | A full Visual Studio theme, used only as a token/slot skeleton (category names, GUIDs, which slots are `CT_RAW` vs system/automatic). Its actual colours are discarded. |
| `extract-json.py` | Flattens `source.vstheme` into `src/vstheme-tokens.json`. Run only when the skeleton itself changes (e.g. a new VS release adds/removes tokens). |
| `src/vstheme-tokens.json` | The flattened token list consumed by the generator. Checked in, so contributors don't need to regenerate it for normal palette changes. |
| `src/generate-theme.py` | Maps every token in `vstheme-tokens.json` onto the Gruber Darker palette (`PALETTE`, `EXACT`, `NAME_EXACT`, `FOREGROUND_PATTERNS`, `BACKGROUND_PATTERNS`) and writes `src/generated.vstheme`. This is where palette/mapping changes belong. |
| `src/generated.vstheme` | The theme file actually shipped in the VSIX. Generated — do not hand-edit; re-run `generate-theme.py` instead. |
| `src/audit-theme.py` | Reports which token slots fell through to a generic default instead of an explicit mapping, so coverage regressions are visible. |

## Changing a colour

1. Edit the mapping in `src/generate-theme.py`:
   - Exact token → role overrides go in `EXACT` (keyed by `(category, name)`) or `NAME_EXACT`
     (keyed by `name` alone, for tokens that repeat across categories).
   - Pattern-based fallbacks go in `FOREGROUND_PATTERNS` / `BACKGROUND_PATTERNS`. Earlier
     patterns win, so add specific patterns above general ones.
   - Palette values themselves live in the `PALETTE` dict at the top of the file.
2. Regenerate the theme:
   ```sh
   cd src
   python generate-theme.py
   ```
3. Check mapping coverage:
   ```sh
   python audit-theme.py
   ```
   Aim to reduce "generic foreground default" / "generic background default" counts, not just
   avoid raising them. The audit's category breakdown at the end shows where fallthrough is
   concentrated.

Only run `extract-json.py` if you're regenerating `vstheme-tokens.json` itself from a new
`source.vstheme` skeleton — it will overwrite the checked-in token file, including any tokens
whose Visual Studio-version availability differs from the current one.

Python 3.10+ is required (the scripts use `from __future__ import annotations` and PEP 604
union syntax); no third-party packages are needed, only the standard library.

## Building and debugging the extension

1. Open `gruber-darker-vs.slnx` in Visual Studio 2022.
2. Press **F5**. The project's `StartArguments` (`/rootsuffix Exp`) launches the Visual Studio
   experimental instance with the theme extension installed, rather than your main VS instance.
3. In the experimental instance, switch to **Gruber Darker** via **Tools → Options →
   Environment → General → Color theme** to see your changes.

The built `.vsix` is written to `src/bin/<Configuration>/net472/gruber-darker-vs.vsix`.

## Releasing

Publishing to the Visual Studio Marketplace is handled by `.github/workflows/publish.yml`,
gated behind a manual approval so a stray tag push can't ship a release unattended.

To ship a release:

1. Push a tag matching `vMAJOR.MINOR.PATCH` (e.g. `v0.2.0`). The manifest's checked-in
   `Version` in `src/source.extension.vsixmanifest` is not the source of truth — CI stamps the
   tag's version into it before building.
2. CI builds the VSIX, then waits at the `marketplace` environment for a reviewer to approve.
3. On approval, it publishes via `VsixPublisher.exe` and attaches the built `.vsix` to a
   GitHub Release for the tag.

## Pull requests

- Keep palette/mapping changes and skeleton-regeneration (`extract-json.py` re-runs) in
  separate commits — the latter touches a large generated JSON file and is hard to review
  alongside intentional colour changes.
- Include the relevant `audit-theme.py` output (or a summary of the coverage delta) for any
  change to `FOREGROUND_PATTERNS`, `BACKGROUND_PATTERNS`, `EXACT`, or `NAME_EXACT`.
