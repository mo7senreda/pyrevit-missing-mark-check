# Missing Mark check (pyRevit)

A small read-only pyRevit button for Structural BIM Engineers. It lists structural columns and beams whose **Mark** is empty. Each result is a link in the pyRevit output window; clicking it selects that element in Revit.

## What it checks
- Columns: the Structural Columns category, placed instances only.
- Beams: the Structural Framing category, family instances whose StructuralType is Beam. Braces and other framing are not included (Structural Framing also holds braces).
- Active project model only. It stops with a message if no project is open or a family file is active.
- "Missing" means the Mark parameter is blank, only spaces, or not present on the element.

## What it does not do
- It does not write to the model (no transaction is opened).
- It does not check linked models, other categories, or whether Marks are unique.
- It does not fill Marks in.

## Install
1. Install pyRevit.
2. Copy the `MarkCheck.extension` folder into a folder pyRevit scans (Settings > Custom Extension Directories).
3. Reload pyRevit. A "BIM" tab appears with a "Missing Mark" button.

## Trying it (tested on Revit 2025 only)
1. Open a COPY of a project (or a sample/template model), not the live file.
2. pyRevit tab > Settings > Custom Extension Directories > add the folder that CONTAINS `MarkCheck.extension`. Save settings and reload.
3. Click BIM > Checks > Missing Mark. Results appear in the output window; click an element link to select it in Revit.
4. Cross-check a few results by hand: select a listed element and look at its Mark in Properties.
In Revit 2024 and 2025 `ElementId.Value` exists, so the script takes that path. The script avoids f-strings and runs under IronPython 2.7 syntax as well as CPython. This has not been checked against pyRevit's engines in practice.

## Testing status
- Logic tests with stand-in objects: `tests/test_mark_logic.py`. They do not run the Revit API.
- Manual test by the author in one small sample project on Revit 2025 with pyRevit (pyRevit version not recorded). Observed: the button ran without errors; elements without a Mark were listed; giving one column a Mark removed it from the list; clicking an element number selected it; a beam's level (Level 2) matched its Reference Level in Properties.
- Not tested: the "nothing was checked" message on an empty model, Revit 2024 or any other version, other pyRevit versions, large or workshared models, linked models.
- Experimental. Try it on a copy or a sample model first.

## Licence
MIT. See the LICENSE file. Copyright (c) 2026 Mohsen Reda.
