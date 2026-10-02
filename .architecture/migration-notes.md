# Architecture revision 2 — migration notes

WIP evidence gathered while executing architecture contract revision 2
(`ARCHITECTURE.md` + `.architecture/handoff.json`) plus the approved human
addendum. Pure discovery: **no product code has been modified at this point.**

These notes exist so the migration can resume without re-deriving the same
facts. They are not normative — the contract remains authoritative.

## 1. Environment baseline

| Item | Value |
|---|---|
| Baseline | `main` @ `6be29fe437a7cd992d4e079f71720821b25216b9` (v0.5.7) |
| Python | 3.14.7 (`/usr/bin/python`) |
| OS | CachyOS Linux 7.2.7 |
| uv | 0.12.5 |
| Machine | 3.7 GB RAM, 2 CPUs |

**Collection verified exactly:** `pytest -q -m "not slow" --collect-only`
→ `3536/4341 tests collected (805 deselected)` in 10.75 s, matching the contract.

System Python carries only `numpy 2.5.3`, `PySide6 6.11.2`, `pytest 9.1.1`.
`openskp`, `ezdxf`, `manifold3d` and `mapbox_earcut` are **absent**, so
`python main.py --check` exits **1** (`NOT OK — missing mapbox_earcut,
manifold3d`) before the UV migration. Missing dependencies produce *skips*,
not failures.

### 1.1 The single-process test command is not reproducible here

`systemd-oomd` kills a full single-process run:

```text
ingetrazo-baseline.service: systemd-oomd killed 130 process(es) in this unit.
Main process exited, code=killed, status=9/KILL
1.9G memory peak, 1.4G memory swap peak   (on a 3.7G box, at ~14 % progress)
```

Qt/GL fixtures accumulate across tests in one interpreter. This is an
environment property, not a contract defect. **Effective command** (the
contract asks for "comandos efectivos" to be recorded): shard by test file
with a fresh interpreter per shard and aggregate, which is equivalent because
the tests are independent.

```bash
mapfile -t F < <(ls tests/test_*.py | sort)
for ((i=0; i<${#F[@]}; i+=24)); do
  QT_QPA_PLATFORM=offscreen python -m pytest -q -m "not slow" \
      -p no:cacheprovider "${F[@]:i:24}"
done
```

396 test files → 17 shards. Verified: shard 1 = 177 passed in 69 s.

## 2. UV feasibility (scratch-dir probe, repo untouched)

`uv lock` resolves 23 packages in ~7 s.

- openskp 1.3.0 pinned to
  `rev=291700bc213655a00461838de71e5f206311e619#291700bc213655a00461838de71e5f206311e619`
  — the approved SHA exactly.
- Root project records `source = { virtual = "." }` → **no build backend is
  introduced and the project is not installed**, as the contract requires.
- `requires-python = ">=3.11"` honoured.
- Transitive additions (`defusedxml`, `mapbox-earcut`, `shapely`, `trimesh`)
  are openskp's own dependencies → **no new direct runtime dependency**.

**Caveat:** `[tool.uv] version-path` is **not supported by uv 0.12.5**
(`unknown field`). Version must therefore be static in `pyproject.toml` even
though `core/version.py` is the application's source of truth — so a drift
guard is needed so the two cannot diverge.

## 3. WU-UV-01 dependency consumer inventory

**Verdict: `requirements.txt` has real technical (packaging) consumers**, so
the contract's *KEEP as generated artifact* branch applies, **not DELETE**.

| Class | Location | What |
|---|---|---|
| CI | `.github/workflows/ci.yml:58` | `pip install -r requirements.txt` |
| **Packaging** | `.github/workflows/release-macos.yml:33` | filters `pytest` out of `requirements.txt` into `reqs.txt` |
| **Packaging** | `packaging/flatpak/com.ingetrazo.IngeTrazo.yml:69` | same filter inside `flatpak-builder` |
| Documentation | `README.md:205-213`, `CONTRIBUTING.md:9-24`, `docs/development.md:4-17` | `python3 -m venv venv` + `pip install -r requirements.txt` |

Not consumers (comment/prose only): `tests/test_ifc_validation.py:8`,
`docs/skp-backend.md:19`, `ARCHITECTURE.md`, `.architecture/handoff.json`.

`runtime-consumers`: **none.** No production module reads dependencies.
`ingetrazo.spec` declares `hiddenimports` for PySide6 / ezdxf / manifold3d /
`collect_submodules('openskp')` and consumes the installed environment, never
`requirements.txt`. `installer/ingetrazo.iss` has zero dependency references.

Out of scope (self-contained packaging that does not depend on our development
install method): `build-windows.yml:35-63`, `release.yml:40-148`.

### Real `venv/` functional consumers beyond documentation

| Location | Reference |
|---|---|
| `scripts/release_check.sh:20` | `PY="$HERE/venv/bin/python"` |
| `scripts/install_desktop.sh:49` | `Exec=$ROOT/venv/bin/python` |
| `packaging/build-appimage.sh:24` | `PYTHON=${PYTHON:-$ROOT/venv/bin/python}` (overridable) |
| `packaging/build-macos-app.sh:26` | `PYTHON=${PYTHON:-$ROOT/venv/bin/python}` (overridable) |

`.gitignore` already ignores **both** `venv/` and `.venv/` (lines 8-9), so no
ignore change is needed.

## 4. Export surface — evidence for the addendum B decision

`_on_export_stl / _obj / _glb / _dae` are 3-6 lines delegating to
`formats/<fmt>.py:save_*`. `_on_export_ifc` (23), `_on_export_view_dxf` (38)
and `_on_export_image` (29) are dialog + one compute + one write.
`_export` is a dialog + writer delegate.

**No export carries threading, staging, progress, several steps or substantial
coordination.** Therefore: **no `views/exports/` and no `architecture_conflict`**
— exports stay thin UI actions delegating to the real owner in `formats/`.

## 5. Composer map (`views/composer.py`, 12,506 lines)

| Zone | Lines | Target |
|---|---|---|
| header + mm-space painters | 1-2211 | `painters.py` |
| item classes (`_SheetItem` + 16 types, `GuideItem`, `RulerWidget`, `InlineTextEditor`) | 2212-3850 | `items.py` |
| `ComposerCanvasView` | 3851-5227 | `canvas.py` |
| `ComposerWindow` (499 methods) | 5228-12506 | `window.py`, then `panels/`, `output.py` |

### 16 real property panels (matching the 16 sheet item types)

`_page_none` (6296) is the empty-state placeholder, not an item panel.

| panel | lines | size | | panel | lines | size |
|---|---|---|---|---|---|---|
| `_page_frame` | 6307 | **339** | | `_page_etiqueta` | 7046 | 63 |
| `_page_cota` | 6810 | 130 | | `_page_cota_ang` | 7202 | 62 |
| `_page_cajetin` | 7337 | 115 | | `_page_image` | 7264 | 59 |
| `_page_cota_rad` | 7109 | 75 | | `_page_text` | 6646 | 51 |
| `_page_forma` | 6724 | 70 | | `_page_llamada` | 6940 | 41 |
| `_page_nivel` | 6981 | 65 | | `_page_norte` | 6697 | 15 |
| `_page_perfil` | 7485 | 65 | | `_page_scalebar` | 7470 | 15 |
| | | | | `_page_leyenda` | 6712 | 12 |
| | | | | `_page_angle` | 9452 | 9 |

Addendum A: one module per owner; a shared module only where several items
have **exactly identical** property behaviour. The four small panels are
candidates for sharing **only if** behaviour proves identical — verify, do not
assume.

### Import surface

59 test files reference `views.composer`; 42 names arrive via
`from views.composer import …`, plus module-alias attribute access.
Only **two** tests patch composer module internals and will need their patch
target moved to the owner module after the split:

- `tests/test_composer_items_panel.py:145` → patches `paint_text_mm`
- `tests/test_composer_perfil.py:152` → patches `_draw_text_mm`

(owner for both is `painters.py`). Every other `composer.X = …` in tests is a
`ComposerWindow` *instance* attribute, not the module.
`tests/test_vector_frame_drag_is_bounded.py:134` uses
`inspect.getsource(ComposerWindow._paint_sheet)`.

## 6. The 9 upward seams (all confirmed at the contract's exact lines)

| # | Site | Current | Method |
|---|---|---|---|
| 1 | `core/autosave.py:44` | `from formats import igz` | writer callback parameter |
| 2 | `core/library.py:219` | `from formats.obj import Y_UP_TO_Z_UP` | relocate the constant into `core/` — **both `core/geometry.py` and `core/orient.py` already exist; pick the true orientation owner rather than adding a module** |
| 3 | `core/solids.py:203` | `from formats.fuse import fuse_coplanar_loops` | parameter injection |
| 4 | `core/render_blender.py:398` | `from formats.gltf import save_glb` | parameter injection |
| 5 | `core/history.py:2622` | `from formats.fuse import simplify_mesh` | parameter injection |
| 6 | `core/history.py:3587` | `from georef.datum import SceneDatum` | georef-owned factory it is handed |
| 7 | `core/extensions.py:130` | `from tools.base import Tool` | parameter injection |
| 8 | `tools/select.py:21` | top-level `from views import prompts` | injected dependency |
| 9 | `tools/solid_tools.py:135` | `from views.icons import solid_cursor` | received from caller |

`georef → views/tools/formats` and `formats → views/tools` are already clean,
so only 1-9 need work.

## 7. Viewport picking zone (`views/viewport.py`, 12,949 lines)

Candidate moves to `core/picking.py`: `_visible_spans` (8684),
`_tex_run_spans` (8709), `_pick_lazy_table` (8734), `_pick_materialize` (8765),
`_visible_depth_limit` (8883), `_placements_under_px` (8911), `_pick_index`
(8939), `_pick_static_tris` (9286), `_pick_flat` (9302), `_expand_placements`
(2462).

Each must first be checked for **material** GL/Qt-widget-state dependence; if it
genuinely depends on widget state it stays in `viewport.py` and the evidence is
recorded.

## 8. Existing tooling

No `ruff`, `mypy`, `black`, `.cfg` or lint configuration exists anywhere, and
`scripts/` has no check/lint script. `check_architecture.py` will be the first
and must stay a plain stdlib script — the contract forbids adding linter tooling.