# IngeTrazo architecture contract revision 2 execution plus approved UV migration

Work ID: ingetrazo-arch-rev2
Status: active
Mode: structured

## Goal
Transform IngeTrazo incrementally and behavior-preserving to reduce cognitive scope, improve agent locality, make architectural boundaries mechanically verifiable and leave a reproducible UV-based development environment. UV migration lands first; then the 9 upward seams close, core/picking.py owns the Qt-free spatial engine, views/composer/ replaces the monolith with a SHEET_ITEM_SPECS registry and per-owner panels/, and views/imports/ owns the import workflows, leaving MainWindow as composition plus thin actions.

## Work Units
- [~] WU-1 — WU-00 Baseline record
  - Touched Files: [".architecture/handoff.json",".architecture/migration-notes.md","ARCHITECTURE.md"]
  - Requirements: REQ-1, REQ-2
  - Constraints: 
  - Acceptance: Both baseline suites are executed and their collected/passed/skipped counts, the commit, working-tree state, Python version and OS are recorded. Characterization tests exist only for the three gaps the contract names. No refactor has started.
  - Expected Files: ["requirements.txt","tests"]
- [ ] WU-2 — WU-UV-01 Dependency consumer inventory
  - Requirements: REQ-3
  - Constraints: CON-4, CON-9
  - Acceptance: Every real consumer of requirements.txt, pip install, python -m venv and pytest is located deterministically and classified as runtime, CI, packaging or documentation consumer, inspected at least in README.md, CONTRIBUTING.md, .github/workflows/**, packaging/**, installer/**, scripts/** and ingetrazo.spec. Nothing is modified in this unit.
  - Expected Files: []
- [ ] WU-3 — WU-UV-02 pyproject.toml
  - Requirements: REQ-4
  - Constraints: CON-1, CON-2, CON-3, CON-4
  - Acceptance: A minimal pyproject.toml declares name ingetrazo, requires-python >=3.11, the five approved runtime dependencies, the dev group with pytest>=8.0 only and the [tool.uv.sources] openskp git/rev/subdirectory entry. No code is moved and no invented metadata is added.
  - Expected Files: ["pyproject.toml"]
- [ ] WU-4 — WU-UV-03 Lock and clean sync
  - Requirements: REQ-5, REQ-6
  - Constraints: CON-1, CON-2, CON-3, CON-5, CON-4
  - Acceptance: uv lock and uv sync succeed. Runtime imports of PySide6, numpy, ezdxf, manifold3d and openskp resolve, openskp provably comes from the approved Git SHA, uv run python main.py --check passes and the not-slow suite passes at or above baseline. uv.lock is never hand-edited.
  - Expected Files: ["pyproject.toml","uv.lock"]
- [ ] WU-5 — WU-UV-04 CI and developer workflow
  - Requirements: REQ-7, REQ-8
  - Constraints: CON-1, CON-9, CON-4
  - Acceptance: Only real consumers are updated. CI installs through the lockfile with uv sync --locked and uv run --locked pytest -q -m 'not slow'. README, CONTRIBUTING and the development guide show the uv quick start and no longer instruct python -m venv plus pip install -r requirements.txt. Packaging that does not depend on the development install method is untouched.
  - Expected Files: [".github/workflows/ci.yml","CONTRIBUTING.md","README.md","docs/development.md"]
- [ ] WU-6 — WU-UV-05 requirements.txt disposition and UV gate
  - Requirements: REQ-9, REQ-22
  - Constraints: CON-1, CON-3, CON-5, CON-4
  - Acceptance: The disposition follows only the WU-UV-01 evidence: deleted when no technical consumer exists, otherwise kept solely as a generated artifact from uv.lock with a drift guard and pyproject.toml plus uv.lock documented as authoritative. Never two manual sources. Then rm -rf .venv, uv sync --locked, uv run --locked python main.py --check and uv run --locked pytest -q -m 'not slow' all pass before any refactor starts.
  - Expected Files: [".github/workflows/ci.yml","requirements.txt"]
- [ ] WU-7 — WU-02 Contract docs, machine rules and check_architecture
  - Requirements: REQ-10, REQ-11
  - Constraints: CON-4, CON-8
  - Acceptance: ARCHITECTURE.md, .architecture/handoff.json, docs/architecture.md and CONTRIBUTING.md reflect the approved UV migration, views/composer/panels/ as a package, views/imports/ as import-only with exports delegating to formats/, core/picking.py ownership and the final boundaries, without new architecture analysis. scripts/check_architecture.py exists, reads the machine contract, and is added to the verifiable verification loop. The normal run passes at this point and the --completion run reports the remaining migration delta.
  - Expected Files: [".architecture/handoff.json","ARCHITECTURE.md","CONTRIBUTING.md","docs/architecture.md","scripts/check_architecture.py"]
- [ ] WU-8 — WU-SEAM-01 Close the 7 core-to-upper seams
  - Requirements: REQ-12, REQ-13
  - Constraints: CON-4, CON-5, CON-9
  - Acceptance: The 7 core-to-upper seams are closed one at a time by injection, callback, parameter or relocation of genuinely-core constants and math: the autosave writer, the Y_UP_TO_Z_UP constant relocation, the solids fuse writer, the render_blender gltf writer, the history fuse writer, the history SceneDatum resolution and the extensions Tool base. Each seam gets focused tests, an architecture check, the fast suite green and a checkpoint. No workflow is moved down into core/ to satisfy the rule.
  - Expected Files: ["core","formats","georef","tools"]
- [ ] WU-9 — WU-SEAM-02 Close the 2 tools-to-views seams
  - Requirements: REQ-12, REQ-13
  - Constraints: CON-4, CON-5
  - Acceptance: The 2 tools-to-views seams are closed by injection: tools/select.py receives the prompts module and tools/solid_tools.py receives the cursor from its caller. Focused tests, architecture check, fast suite green and a checkpoint.
  - Expected Files: ["tools/select.py","tools/solid_tools.py"]
- [ ] WU-10 — WU-PICK-01 Extract core/picking.py from views/viewport.py
  - Requirements: REQ-14, REQ-15
  - Constraints: CON-4, CON-5, CON-6, CON-7
  - Acceptance: core/picking.py owns the Qt-free and GL-independent pick index, placement span construction, lazy placement expansion, bounding/culling structures, visible spans, tex-run spans, static/flat pick structures, placements-under-pixel, depth-under-cursor and ray/spatial math. views/viewport.py keeps QOpenGLWidget, GL context and state, shaders, render passes, frame pacing, Qt input, overlays and thin delegating pick_* entry points, with no spatial-index construction left. Every function is checked for material widget-state dependence first, and one that depends on it stays in viewport with recorded evidence. No mixins, no subclass decomposition, no renderer rewrite. Behavior and performance unchanged.
  - Expected Files: ["core/picking.py","views/viewport.py"]
- [ ] WU-11 — WU-COMPOSER-01 Create the views/composer package seam
  - Requirements: REQ-16
  - Constraints: CON-4, CON-5, CON-6
  - Acceptance: views/composer/ exists as a package whose __init__.py preserves the complete existing import surface, so views/main_window.py and every referencing test file keep resolving unchanged. No module is renamed and no behavior changes.
  - Expected Files: ["views/composer/__init__.py"]
- [ ] WU-12 — WU-COMPOSER-02 Extract painters.py
  - Requirements: REQ-16
  - Constraints: CON-4, CON-5, CON-6
  - Acceptance: The mm-space painter functions move mechanically into views/composer/painters.py with the import surface preserved. No behavior change during extraction. Fast suite green and a checkpoint.
  - Expected Files: ["views/composer/painters.py"]
- [ ] WU-13 — WU-COMPOSER-03 Extract items.py
  - Requirements: REQ-16
  - Constraints: CON-4, CON-5, CON-6
  - Acceptance: _SheetItem and the sheet item classes move mechanically into views/composer/items.py with the import surface preserved. No behavior change during extraction. Fast suite green and a checkpoint.
  - Expected Files: ["views/composer/items.py"]
- [ ] WU-14 — WU-COMPOSER-04 Extract canvas.py
  - Requirements: REQ-16
  - Constraints: CON-4, CON-5, CON-6
  - Acceptance: ComposerCanvasView with its input, placement and selection dispatch moves mechanically into views/composer/canvas.py with the import surface preserved. No behavior change during extraction. Fast suite green and a checkpoint.
  - Expected Files: ["views/composer/canvas.py"]
- [ ] WU-15 — WU-COMPOSER-05 Extract window.py
  - Requirements: REQ-16
  - Constraints: CON-4, CON-5, CON-6
  - Acceptance: ComposerWindow with composition, caches and undo wiring moves mechanically into views/composer/window.py with the import surface preserved. No behavior change during extraction. Fast suite green and a checkpoint.
  - Expected Files: ["views/composer/window.py"]
- [ ] WU-16 — WU-COMPOSER-06 Extract output.py
  - Requirements: REQ-16
  - Constraints: CON-4, CON-5, CON-6
  - Acceptance: PDF, DXF, image, print and HLR output moves mechanically into views/composer/output.py with the import surface preserved. No behavior change during extraction. Fast suite green and a checkpoint.
  - Expected Files: ["views/composer/output.py"]
- [ ] WU-17 — WU-REGISTRY Introduce views/composer/registry.py and migrate one item type at a time
  - Requirements: REQ-17
  - Constraints: CON-4, CON-5, CON-7
  - Acceptance: SHEET_ITEM_SPECS becomes the single record of sheet item types. Positional panel indices, duplicated per-type _rebuild_canvas blocks, the place_tool per-type if/elif, per-type selection isinstance dispatch and duplicated toolbar/type metadata are replaced by registry lookups one item type at a time, each with tests and a checkpoint. Before completion, adding a throwaway item type end-to-end proves that one registration plus its painter, item and panel owner is enough with no edits to multiple dispatch chains, and the throwaway type is then removed. The registry is not a plugin API.
  - Expected Files: ["views/composer/canvas.py","views/composer/registry.py","views/composer/window.py"]
- [ ] WU-18 — WU-PANELS Extract views/composer/panels/ by owner
  - Requirements: REQ-18, REQ-17
  - Constraints: CON-4, CON-5, CON-9
  - Acceptance: The property panels live in views/composer/panels/ as cohesive per-owner modules. One module per sheet item when it has its own behavior; shared modules only when several items have exactly identical property behavior; SHEET_ITEM_SPECS points at the corresponding panel. No God module and no common.py or helpers.py dumping ground without real shared-behavior evidence. Fast suite green and a checkpoint.
  - Expected Files: ["views/composer/panels"]
- [ ] WU-19 — WU-IMPORTS Extract import workflows into views/imports/ by family
  - Requirements: REQ-19, REQ-20
  - Constraints: CON-4, CON-5, CON-6, CON-7
  - Acceptance: views/imports/ holds __init__.py, skp.py, meshes.py, cad.py, imagery.py and geodata.py and is exclusively for import workflows. Each family module owns its dialog, parse orchestration, worker/thread, progress, staging, conversion to Commands and transactional insertion, while real parsing stays in formats/ or georef/. MainWindow keeps only the QAction, a thin slot and delegation, and holds no threading, staging, parse orchestration, progress logic or multi-step insertion. views/imports/__init__.py holds no exports and no views/exports/ is created; simple exports remain thin UI actions delegating to the real owner in formats/. An export carrying substantial workflow of its own is recorded as architecture_conflict instead of being silently relocated. Fast suite green and a checkpoint after each family.
  - Expected Files: ["views/imports","views/main_window.py"]
- [ ] WU-20 — WU-MAINWINDOW Verify final MainWindow ownership
  - Requirements: REQ-21
  - Constraints: CON-9, CON-8
  - Acceptance: MainWindow ownership is verified against the contract by evidence, not by an arbitrary line-count target. Window composition, menu and toolbar wiring, docks, QAction creation, document lifecycle, thin action slots and tool registration remain; no import pipeline, substantial format logic, picking or spatial math, composer item implementation or generic dumping-ground workflow remains.
  - Expected Files: ["views/main_window.py"]
- [ ] WU-21 — WU-DOCS-FINAL Final documentation and contract check
  - Requirements: REQ-10, REQ-22, REQ-23
  - Constraints: CON-4, CON-8
  - Acceptance: Only affected documentation is updated: README.md, CONTRIBUTING.md, docs/architecture.md, ARCHITECTURE.md and .architecture/handoff.json. README and CONTRIBUTING present UV as the standard development workflow and obsolete manual venv or pip instructions are gone unless an explicitly documented compatibility remains. Documentation is not expanded beyond scope. The full final verification sequence passes from a clean checkout.
  - Expected Files: [".architecture/handoff.json","ARCHITECTURE.md","CONTRIBUTING.md","README.md","docs/architecture.md"]

## Next

WU-1 — active outcome

## Lifecycle

- WU-1: pending → active
