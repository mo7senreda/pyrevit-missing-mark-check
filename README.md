# Missing Mark check (pyRevit)

A small read-only pyRevit button for Revit. It lists model elements whose **Mark** is empty, grouped by category. Each result is a link in the pyRevit output window; clicking it selects that element in Revit.

## What it checks
- Elements in the active project that have a Model-type category, in all phases and all design options. Demolished elements are included. Nothing depends on the active view.
- Only elements that have the built-in Mark parameter are checked. "Empty" means the Mark is blank, only spaces, or has no value.
- Elements with no Mark parameter are not flagged. They are counted per category in the summary.
- A geometry/view filter keeps out definitions and helpers that sit in Model-type categories (for example Materials, Legend Components, project information). An element is kept only if it has a model bounding box, is not view-specific, and is not a project base point or internal origin.
- The filter is a heuristic. It does not guarantee that every real model element is covered: a real element whose geometry is unavailable would be excluded too. The excluded elements are counted per category in the "Excluded" column so you can see what was left out.
- If reading an element fails, it is counted as a read error and listed. It is never counted as empty.

## What it does not do
- It does not write to the model (no transaction is opened).
- It does not check linked models, CAD imports, views, annotations, or group containers (group members are checked).
- It does not check Type Mark, only the instance Mark. It does not check whether Marks are unique, and it does not fill Marks in.

## Output
- A summary table per category: checked, empty Mark, no Mark parameter, read errors, excluded.
- Then a table per category of the elements with an empty Mark (link, type, level). Each table shows at most 300 rows; the summary has the full count.
- A progress bar with a Cancel button. A cancelled run is marked as a partial result.

## Install
1. Install pyRevit.
2. Copy the `MarkCheck.extension` folder into a folder pyRevit scans (Settings > Custom Extension Directories).
3. Reload pyRevit. A "BIM" tab appears with a "Missing Mark" button. The button icon is `icon.png`; `icon.dark.png` is used on the dark theme in Revit 2024 and later.

## Testing status
- Logic tests with stand-in objects: `tests/test_mark_logic.py`. They do not run Revit or the Revit API.
- Manual test by the author on one small sample project in Revit 2025 with pyRevit. The button ran with no read errors and showed the summary. Without the geometry filter, 191 Materials were counted as empty, which is why the filter exists. After adding it, the Materials moved to the Excluded column. The author set a Mark on one listed foundation and the empty count went down by one (reported by the author, not checked from a screenshot).
- Not tested: design options, demolished elements, the Cancel button, large or workshared models, linked models, Revit versions other than 2025, other pyRevit versions.
- Experimental. Try it on a copy or a sample model first.

## Licence
MIT. See the LICENSE file. Copyright (c) 2026 Mohsen Reda.
