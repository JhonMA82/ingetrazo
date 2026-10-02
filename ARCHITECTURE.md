# IngeTrazo Architecture Contract

**Status:** final. Architecture revision 2. This document is the decided architecture for this repository, not a proposal and not a roadmap.
**Baseline analyzed:** `main` @ `6be29fe437a7cd992d4e079f71720821b25216b9` (v0.5.7, 1334 commits, clean tree).
**Machine contract:** `.architecture/handoff.json` (identical decisions, executable form). Work Ledger may decompose the contract; it must not reinterpret or change it.

---

## 1. Context and constraints

IngeTrazo is a GPL desktop CAD / 3D modeling application (SketchUp-inspired) with three real product capabilities built on one Qt application:

- a 3D modeling viewport and modeling tools,
- a sheet composer ("Láminas") that prints saved scenes as scaled, exact-metric paper layouts (QGIS-layout model, `QGraphicsScene` in millimetres),
- georeferencing and DEM terrain, plus image/orthophoto/photomesh import, and a plugin + AI-bridge extension model where every mutation is one undoable step.

Constraints that shape every decision below:

- **Single desktop process.** No server, no multi-deployment, no independent service scaling. Distributed architecture is not applicable.
- **Behavior is preserved by this contract.** The `.igz` native schema, the plugin contract (`docs/plugins.md`), shortcut keys, user-visible strings, visual and performance characteristics, and all packaging (`ingetrazo.spec`, `packaging/flatpak`, `packaging/snap`, `installer/`) stay unchanged.
- **Engine logic lives outside the Qt widget.** This is already the dominant convention (`core/snap.py`, `core/hlr.py`, `core/camera.py`, `core/texture.py`, `georef/tiles.py`, and the dependency-minimal doctrine stated at `views/viewport.py:7`). This contract enforces it where it currently leaks.
- **Verification is the test suite.** 4341 tests collected, 3536 under the `not slow` marker, CI gate `.github/workflows/ci.yml` runs `QT_QPA_PLATFORM=offscreen python -m pytest -q -m "not slow"`.
- **Agent-first development is permanent.** Ownership must be findable from the repository alone; every user-facing workflow has one named owner; boundaries must be mechanically checkable.

---

## 2. Current architecture

Flat horizontal layering by technical role at the repository root:

```text
main.py         Qt bootstrap (24.5 KB)
core/     (59)  engine + document model, framework-light
tools/    (31)  modeling tools, one module per tool
georef/   (15)  real-world location: datum, tiles, DEM, photomesh, geotiff, points
formats/  (18)  parse/write: .igz, .skp, obj, stl, dae, gltf/glb, ifc, dxf, dwg bridge
views/    (23)  Qt UI: main_window, viewport, composer, tray, icons, shortcuts, dialogs
plugins/   (6)  runtime-discovered Tools (Model Info, Python Console, AI Bridge, AI Assistant, Solid Inspector, Render Blender)
scripts/, examples/extensions/, i18n/, resources/, materials/, styles/, analysis/,
benchmarks/, packaging/, installer/, docs/, tests/
```

Scale: 575 Python source files, 176,123 source lines, 400 test files, 3082 test functions, 5 locales × ~2460 keys.

### Evidence

**Dependency direction is healthy; there are no import cycles.** Verified by `rg` over every package: `main → views → {tools, formats, georef} → core`, `plugins → {core, tools, views}`, `formats → georef` (7 sites, deliberate: `.igz` serializes georef payloads), `georef → core` (4 files). The inspector's flagged "mutual dependencies" are **9 deferred function-level upward seams**, not cycles:

- `core → upper` (7): `core/autosave.py:44 → formats.igz`, `core/library.py:219 → formats.obj` (constant `Y_UP_TO_Z_UP`), `core/solids.py:203 → formats.fuse`, `core/render_blender.py:398 → formats.gltf`, `core/history.py:2622 → formats.fuse`, `core/history.py:3587 → georef.datum`, `core/extensions.py:130 → tools.base`.
- `tools → views` (2): `tools/select.py:21` (top-level `from views import prompts`), `tools/solid_tools.py:135` (`from views.icons import solid_cursor`).

These are small and fixable, but they mean the layering cannot be enforced mechanically today.

**Qt conventions are respected.** `QMainWindow` composition, `QOpenGLWidget` for the GL surface, `QGraphicsScene`/`QGraphicsView` in millimetres for sheets, `QSettings` for shortcuts and preferences, `core.i18n.tr()` + `QTranslator` for all strings, a deliberately minimal dependency set (`requirements.txt`: PySide6 renders the engine; numpy only for DEM decode).

**Three UI modules own the product's most active workflows, and each has measured locality failure.**

| Change an agent actually makes | Current path | Verdict |
|---|---|---|
| New modeling tool (the real 2026 pattern: Fillet, Walkthrough, Change Axes, Solid Tools, Texture Position) | `tools/<name>.py` (+ `core/<algo>.py` if new) + registration in `views/main_window.py` (36 tool imports, 86 `Tool` references) + `views/icons.py` + `views/shortcuts.py` + i18n + tests | **healthy** — `git log --diff-filter=A -- 'tools/*.py'` shows one module per feature |
| New import format (orthophoto, photomesh, DWG, georef, survey points — all 2026 work) | parse is correctly owned by `formats/` or `georef/`; the **workflow** (dialog + threaded parse + progress + scene insertion + undo) is one of **33 methods in `MainWindow` lines 4798–6048**. `main_window.py` grew 4,668 → 6,172 lines (+32%) in 10 days, almost entirely here | **weak** |
| New sheet item type (16 types exist and the count grows per release) | `views/composer.py` (12,507 lines) needs ~6 insertion points: a painter in the 63-function block (1–2213), an item class (2214–3850), a `for x in self.comp.<coll>: addItem(<X>CanvasItem(...))` block in `_rebuild_canvas` (7759+), a `props.addWidget(_top_aligned(self._page_<x>()))` entry whose position is a **magic index 0–15** (6159–6174), a `place_tool` if/elif (5623), and selection dispatch spread over **62 `isinstance` sites**. 59 test files reference the module, many through private names (`_page_*`, `_paint_hlr_lines_mm`, `_rebuild_canvas`) | **weak** |
| Viewport performance / picking (the active frontier, issue #158, 6 latest commits) | the pick index, lazy placement spans and vectorised span cull are implemented **inside the Qt widget**: 17 `pick*` methods plus `_pick_index`, `_pick_lazy_table`, `_pick_materialize`, `_pick_static_tris`, `_pick_flat`, `_placements_under_px`, `_visible_spans`, `_visible_depth_limit`, `_expand_placements` (2343–9500 of a 12,950-line file). No `core/` spatial module exists | **weak** — Qt-free ray/geometry work is untestable without Qt and invisible from `core/` |

**Cohesive large modules are not problems.** `core/history.py` (4,054 lines, 90 `Command` classes, largest method 101 lines) is the undo engine every mutation flows through — one reason to change. `views/tray.py` (4,014 lines, 18 panel classes) and `views/icons.py` (2,055 lines, icon registry) are cohesive by nature. Size alone is not a verdict; these are not split.

**i18n friction is governed.** The 5 locale files are the highest-churn paths in the repository (34–54 commits each), but parity is mechanically enforced by `tests/test_translation_files.py`. That is acceptable friction and stays as it is.

**Documentation drift.** `docs/architecture.md` claims ModernGL is the OpenGL wrapper; `requirements.txt` and `views/viewport.py:7` state the engine runs on PySide6 alone (ModernGL appears only as a rejected option). It also omits most current packages. Product-intent documents (`docs/composer-plan.md`, `docs/plugins.md`, `docs/skp-backend.md`, `docs/ai-bridge.md`) are accurate and authoritative for product behavior.

### Prior session correction

Revision 1 of this contract (baseline `93a428c`, 2026-09-21) cited `.engineering/PATTERNS.md`, `.engineering/consistency.yml`, `.engineering/aicontext.toml` and an `aicontext check` command. **None of those paths exist in this repository or anywhere in its git history** (`git log --all -- .engineering` and `-- ARCHITECTURE.md` are empty), and the deterministic inspector reports no project-native or configured analysis tooling at this baseline. That evidence base is withdrawn; every claim in this contract is re-derived from the current tree. Revision 1 also froze `views/viewport.py` as unsplit — the six latest commits contradict that premise, and this revision replaces it with §6's zoning rule and the `core/picking.py` extraction.

---

## 3. Intervention

**ORGANIZE.**

The fundamental architectural model is correct, framework-native, and preserved: framework-light engine core, capability packages, Qt view layer, plugins on top, one process. There are no cycles, no misplaced architectural model, no violated framework convention, and no deployment mismatch — so **RESTRUCTURE is not justified**. ORGANIZE is justified by concentrated, measurable agent friction in three UI modules that own the most active workflows, plus 9 seams that block mechanical enforcement of an otherwise-correct layering.

---

## 4. Final target architecture

**Pattern:** Qt-native layered modular monolith (unchanged at the root) + two selective feature slices inside `views/` + one engine extraction into `core/`.

Four decisions, all evidence-driven:

1. **The root package layout is preserved exactly.** No `src/`, no root `features/`. Moving the layers would add churn without improving locality.
2. **The sheet composer becomes a feature slice.** `views/composer/` is split along the physical zones the file already has, and one declarative registry becomes the single extension point for sheet item types.
3. **Import/export workflows become a feature slice.** `views/imports/` owns the pipelines by capability family, with one named owner per family. `MainWindow` keeps composition and thin action slots.
4. **Picking returns to the engine.** `core/picking.py` takes the Qt-free ray/placement-index/span-cull math; `views/viewport.py` keeps GL state, render passes, input events, and thin `pick_*` entry points that delegate.

---

## 5. Final repository structure

```text
main.py                     Qt bootstrap only (unchanged role)

core/                       L0 engine + document model. Imports: stdlib, numpy, minimal PySide6.
                            MUST NOT import tools/, views/, formats/, georef/ in any form.
  picking.py                NEW  ray/placement pick index, lazy placement spans, span cull,
                                depth-under-cursor math (extracted from views/viewport.py)
  history.py                undo engine — Command subclasses (not split, see §9)
  composition.py            sheet ("Láminas") document model + commands — stays in core/
  snap.py hlr.py mesh.py topology.py camera.py scene.py geometry.py units.py
  materials.py style.py saved_views.py sections/... i18n.py extensions.py autosave.py   (unchanged roles)

tools/                      L1 modeling tools, one module per tool. Imports: core/ + georef/.
                            MUST NOT import views/.
georef/                     L1 real-world location. Imports: core/ only.
formats/                    L1 parse/write. Imports: core/ + georef/.

views/                      L2 Qt UI. Imports: core/ + tools/ + formats/ + georef/.
  main_window.py            composition: menus, toolbars, docks, status bar, actions, and
                            thin import/export action slots wired to views/imports/
  viewport.py               the single QOpenGLWidget owner of GL state, render passes and
                            input events; delegates ray/geometry work to core/picking.py
  composer/                 NEW sheet-composer ("Láminas") UI slice
    __init__.py             permanent public re-export surface
    registry.py             SHEET_ITEM_SPECS — the single sheet-item extension point
    painters.py             mm-space painters (the 63 module functions)
    items.py                _SheetItem + the 16 sheet item classes
    canvas.py               ComposerCanvasView — input, placement, selection dispatch (registry-driven)
    window.py               ComposerWindow — composition, caches, undo wiring
    panels.py               the 16 property panels
    output.py               PDF / DXF / image / print / HLR output
  imports/                  NEW import/export workflow owners, by capability family
    __init__.py             registries + entry points used by views/main_window.py
    skp.py                  SketchUp .skp import
    meshes.py               obj, stl, glb, dae
    cad.py                  dxf, dwg (via the LibreDWG bridge)
    imagery.py              image planes, orthophoto, photomesh
    geodata.py              survey points, georef bundles
  tray.py icons.py shortcuts.py sheet_tabs.py extension_api.py status_hints.py theme.py
  prompts.py ndof_input.py toasts.py *_dialog.py filedialogs.py tooltips.py
  fold_section.py profile_panel.py                                             (unchanged roles)

plugins/  scripts/  examples/extensions/  tests/  docs/  i18n/  resources/
materials/  styles/  analysis/  benchmarks/  packaging/  installer/              (unchanged roles)
```

---

## 6. Ownership

Every user-facing capability has exactly one owner. No generic `workflows.py`, `services.py`, `handlers.py` or `helpers.py` module owns unrelated product behavior.

| Capability / workflow | Owner |
|---|---|
| Sheet item type ("Láminas") — adding one | `views/composer/registry.py` (one `SHEET_ITEM_SPECS` entry) → `views/composer/painters.py` + `views/composer/items.py` + `views/composer/canvas.py` + `views/composer/panels.py`; model/command in `core/composition.py` |
| Sheet window composition, caches, undo wiring | `views/composer/window.py` |
| Sheet canvas interaction, placement, selection dispatch | `views/composer/canvas.py` |
| Sheet output (PDF, DXF, image, print, HLR frames) | `views/composer/output.py` (+ `formats/dxf_out.py` for writing) |
| SketchUp `.skp` import workflow | `views/imports/skp.py` |
| Mesh import workflow (obj, stl, glb, dae) | `views/imports/meshes.py` |
| CAD import workflow (dxf, dwg) | `views/imports/cad.py` |
| Imagery import workflow (image planes, orthophoto, photomesh) | `views/imports/imagery.py` |
| Geodata import workflow (survey points, georef) | `views/imports/geodata.py` |
| File export workflow (stl, obj, glb, dae, ifc, view dxf, image, print) | `views/imports/__init__.py` (shared `_export` entry point) |
| Format parsing / writing | `formats/<fmt>.py` |
| Picking, placement index, span cull, depth-under-cursor math | `core/picking.py` |
| GL render passes, frame pacing, camera/zoom/orbit input | `views/viewport.py` |
| Modeling tool | `tools/<name>.py` |
| Snapping / inference | `core/snap.py` |
| Document mutation and undo | `core/history.py` |
| Document model (scene, saved views, sheets, dimensions, texts) | `core/*.py` |
| Panels, docks, tray | `views/tray.py` |
| Menus, toolbars, status bar, application composition | `views/main_window.py` |
| User-visible strings | `core/i18n.py` `tr()` + `i18n/<locale>.json` |
| Plugin discovery and contract | `core/extensions.py` + `plugins/*.py` |
| MCP / AI bridge | `plugins/ai_bridge.py` + `scripts/ingetrazo_mcp.py` |

### Zoning rules

- **`views/viewport.py`:** new ray, geometry, spatial-index, picking or math logic goes to `core/`; new GL state, shaders, render passes or Qt event handling goes here. The file does not grow a second ownership reason.
- **`views/composer/`:** a new sheet item type is added through `registry.py` only. Placement, panel construction, canvas rebuild and selection dispatch are registry lookups — no per-type `isinstance` chain, no positional panel index.
- **`views/imports/`:** a new format joins an existing family module, or a new family module with its own name. It never lands in `main_window.py`.
- **`views/composer/*` and `views/imports/*` are reached only through their `__init__.py` surface** (or their declared module API), never through another slice's private internals.

---

## 7. Dependency rules

**Allowed:**

```text
main.py → views
views  → core, tools, formats, georef
plugins → core, tools, views
tools  → core, georef
formats → core, georef
georef → core
```

**Forbidden:**

- `core` → `tools`, `views`, `formats`, `georef` — including function-level deferred imports.
- `tools` → `views`, `formats`.
- `georef` → `views`, `tools`, `formats`.
- `views` reaching another slice's private internals (`views/composer/*`, `views/imports/*` expose an explicit surface only).

**Enforcement:** `.architecture/handoff.json` carries these as machine-checkable rules (`forbid_python_import`, `require_path`, `forbid_path`) verified by `python scripts/check_architecture.py <target>` (normal run = rules already true at this baseline; `--completion` = the full migration delta). The check is added to the local/CI verification loop.

---

## 8. Framework conventions to preserve

- PySide6 is the framework. `QMainWindow` is composition, not a container for product workflows.
- The sheet composer stays a `QGraphicsScene`/`QGraphicsView` in paper millimetres (QGIS-layout precedent, `docs/composer-plan.md`).
- The viewport stays a Qt-managed `QOpenGLWidget`; the engine stays outside it.
- Signals/slots for UI interaction; direct calls where ownership is direct and synchronous.
- Every document mutation goes through a `Command` in `core/history.py`, so undo and the AI/MCP bridge stay transactional.
- All user-visible strings go through `core.i18n.tr()`; locale files stay flat JSON with parity enforced by `tests/test_translation_files.py`.
- Plugins contribute `Tool` subclasses only (`docs/plugins.md`); `SHEET_ITEM_SPECS` is internal, not a plugin extension point.
- Generated/derived artifacts stay clearly separated: no hand-edited `.ui`/generated Python is introduced by this contract; `i18n/*.json` and `resources/**` are data, `benchmarks/results/*.json` are generated output.
- The minimal-dependency policy in `requirements.txt` stands: no new runtime dependency is added by this contract.

---

## 9. Migration instructions

Behavior-preserving, strangler-fig, in this order. The suite stays green after every step.

**Step 0 — Baseline and characterization.** Record `QT_QPA_PLATFORM=offscreen python -m pytest -q -m "not slow"` green (3,536 tests). Add characterization tests where structural moves would otherwise leave behavior unpinned: property-panel dispatch by selection, `_rebuild_canvas` selection restore, import progress/threading paths.

**Step 1 — Contract docs and rules first, no code moves.** This document lands. Correct the ModernGL paragraph and package list in `docs/architecture.md`. Extend the folder-layout list in `CONTRIBUTING.md` with `views/composer/`, `views/imports/`, `core/picking.py`. Add `.architecture/handoff.json` to the local and CI verification loop.

**Step 2 — Close the 9 upward seams.** One at a time, by injection or relocation, never by moving code down a layer:
`core/autosave.py` takes the writer as a callback/parameter; `Y_UP_TO_Z_UP` moves from `formats/obj.py` to `core/geometry.py` (or `core/orient.py`) and `core/library.py` imports it from there; `core/solids.py`, `core/render_blender.py` and `core/history.py:2622` take the fuse/GLB writers as parameters; `core/extensions.py` receives the `Tool` base as a parameter instead of importing `tools.base`; `core/history.py:3587` resolves `SceneDatum` through a core-level representation or a georef-owned factory call it is handed; `tools/select.py` receives the prompts module as an injected dependency; `tools/solid_tools.py` receives the cursor from its caller. Then flip the `core` and `tools` rules to enforced in the architecture check.

**Step 3 — Extract `core/picking.py` from `views/viewport.py`.** Move the pick index, lazy placement expansion/bbox/frame, span construction and culling, visible-span/tex-run-span logic, static/flat pick structures, placements-under-pixel and depth-under-cursor math. `viewport.py` keeps GL state, shaders, render passes, input events and thin `pick_*` methods that delegate. This is the highest-value move for the active performance frontier and it is deliberately first among the code moves.

**Step 4 — Split `views/composer.py` into `views/composer/`.** Pure move along existing zones: `painters.py`, `items.py`, `canvas.py` (`ComposerCanvasView`), `window.py` (`ComposerWindow`), `output.py`, `panels.py`. `views/composer/__init__.py` keeps a permanent re-export of `ComposerWindow`, `ComposerCanvasView`, the item classes and the painter functions so `views/main_window.py:3679` and the 59 test files keep resolving unchanged. Expand-contract: nothing is renamed until every caller has moved.

**Step 5 — Introduce `views/composer/registry.py` (`SHEET_ITEM_SPECS`).** One entry per sheet item type carrying: model collection name, item class, painter(s), property-panel builder, placement tool, label/icon. Convert the 16 `props.addWidget(...)` magic indices to registry lookups, the per-type `_rebuild_canvas` blocks to one registry-driven loop, `place_tool`'s if/elif to a registry dispatch, and the 62 `isinstance` selection branches to registry lookups keyed by item type. Prove it by adding one throwaway item type end-to-end, then removing it.

**Step 6 — Extract `views/imports/<family>.py`.** From the 33-method block at `MainWindow` 4798–6048, one family at a time — `imagery.py` first (most recent, most duplicated), then `geodata.py`, `cad.py`, `meshes.py`, `skp.py`, then the shared export entry point. Each family module owns its dialog, threaded parse, progress reporting and scene insertion; parsing itself stays in `formats/`/`georef/`. `MainWindow` keeps only the action objects and thin slots wired to the registries in `views/imports/__init__.py`.

**Step 7 — Final verification.** Full non-slow suite, then the `slow` suite, then `python scripts/check_architecture.py <target> --completion` against the finished tree.

---

## 10. Verification

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q -m "not slow"   # 3,536 tests — CI gate
QT_QPA_PLATFORM=offscreen python -m pytest -q                   # 4,341 incl. slow fuzz sweeps
python scripts/check_architecture.py .                         # dependency + ownership rules
python scripts/check_architecture.py . --completion            # full migration delta
```

`scripts/release_check.sh <previous tag> <real .igz>` remains the pre-release gate (bench_session, bench_startup, fast + slow suites, results into `benchmarks/results/<version>.json`). It is unchanged by this contract.

---

## 11. Non-goals

Scoped to this contract unless stated otherwise:

- **Do not split `core/history.py`.** Current evidence does not justify it: 90 cohesive `Command` classes, largest method 101 lines, one reason to change.
- **Do not split `views/tray.py` or `views/icons.py`.** Cohesive panel classes and an icon registry.
- **Do not mixin-decompose or subclass-split the Viewport widget**, and do not replace `QOpenGLWidget` or `QGraphicsScene`.
- **Do not move the sheet model out of `core/composition.py`,** do not change the `.igz` schema, and do not change the plugin contract.
- **Do not migrate i18n to `.ts`/`.qm`** or restructure translation keys; the parity test already governs drift.
- **Do not touch packaging** — PyInstaller spec, Flatpak, Snap, AppImage, Windows installer.
- **Do not add a root `features/` layer, a `src/` layer, or a new build system, dependency manager, linter configuration or indexing service.**
- **Do not generalize the import families into `views/imports/workflows.py`, `handlers.py` or `services.py`.** Explicit per-capability owners are the contract; a dumping ground is a regression.
- **Do not redesign `views/composer/` around a plugin mechanism.** Plugins contribute Tools only.

---

## 12. Completion criteria

The contract is satisfied when all of the following hold:

1. `views/composer/` exists as a package with `views/composer/registry.py`, `views/composer/painters.py`, `views/composer/items.py`, `views/composer/canvas.py`, `views/composer/window.py`, `views/composer/panels.py`, `views/composer/output.py`, and `views/composer.py` no longer exists.
2. Adding a sheet item type requires one `SHEET_ITEM_SPECS` entry plus its painter/panel code: no positional panel index, no new `isinstance` dispatch branch in `canvas.py`, no new block in the canvas rebuild loop.
3. `views/imports/` exists with `skp.py`, `meshes.py`, `cad.py`, `imagery.py`, `geodata.py` and shared export entry points; `views/main_window.py` contains no import/export pipeline — only action objects and thin slots.
4. `core/picking.py` exists and owns the pick index, placement span expansion/cull and depth-under-cursor math; `views/viewport.py` contains GL state, render passes and input handling, with no spatial-index construction.
5. Zero upward seams: no file under `core/` imports `tools`, `views`, `formats` or `georef`; no file under `tools/` imports `views`; no file under `georef/` imports `views`, `tools` or `formats`; no file under `formats/` imports `views` or `tools`.
6. `python scripts/check_architecture.py .` and `... --completion` both pass against the finished tree.
7. `QT_QPA_PLATFORM=offscreen python -m pytest -q -m "not slow"` is green at or above the 3,536-test baseline, and the `slow` suite is green.
8. `.igz` documents written by the baseline version still load; the plugin contract is unchanged; no user-visible string, shortcut key, or visual/performance characteristic changed.
9. `docs/architecture.md` and the `CONTRIBUTING.md` folder layout match this document.