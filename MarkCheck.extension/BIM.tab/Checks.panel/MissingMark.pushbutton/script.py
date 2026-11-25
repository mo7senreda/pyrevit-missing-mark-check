# -*- coding: utf-8 -*-
"""Find model elements whose Mark is empty, grouped by category.

Read only. It opens no transaction and changes nothing in the model.

Scope: elements in the active project document that have a Model-type
category (Category.CategoryType == Model), in ALL phases and ALL design
options, including demolished elements. Nothing is filtered by the active
view. Linked models are not checked.

Geometry/view filter (a heuristic, not proof): an element is checked only if
it has a model bounding box (Element.BoundingBox(None) is not null), is not
view-specific (OwnerViewId is invalid) and is not a project base point or
internal origin. This is meant to keep out definitions and helpers that live
in Model-type categories, such as materials, material assets, pipe segment
definitions, legend components and project information. A real element whose
geometry is unavailable would also be excluded. This check does NOT guarantee
that every real model element is covered. Every excluded element is counted
per category in the "Excluded: no model geometry or view-specific" column.

An element is checked only if it HAS the built-in Mark parameter
(ALL_MODEL_MARK). Elements with no Mark parameter are not counted as missing;
they are counted per category. If reading an element fails, it is counted as a
read error, never as missing and never as "no Mark parameter".
"""
from pyrevit import revit, DB, forms, script

MAX_ROWS_PER_CATEGORY = 300
MAX_ERROR_ROWS = 30
PROGRESS_STEP = 500
UNKNOWN_CATEGORY = "(category could not be read)"


def id_value(element_id):
    """ElementId as an integer. Value exists from Revit 2024; IntegerValue was
    removed in Revit 2026 and is the only option before 2024."""
    if hasattr(element_id, "Value"):
        return element_id.Value
    return element_id.IntegerValue


def mark_state(element):
    """'none' if the element has no Mark parameter (not checked),
    'missing' if Mark is blank or has no value, 'ok' otherwise.
    Raises if the parameter cannot be read; the caller counts that as an error."""
    param = element.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
    if param is None:
        return "none"
    if not param.HasValue:
        return "missing"
    value = param.AsString()
    if value is None or value.strip() == "":
        return "missing"
    return "ok"


REFERENCE_CLASS_NAMES = ["BasePoint", "InternalOrigin"]


def reference_classes():
    """Project/survey base point and internal origin, when this Revit has them."""
    return tuple(getattr(DB, n) for n in REFERENCE_CLASS_NAMES if hasattr(DB, n))


def passes_geometry_filter(element):
    """True if the element passes the geometry/view filter: it has a model bounding
    box, is not view-specific and is not a project reference point.
    Raises on read failure; the caller counts that as an error."""
    if isinstance(element, reference_classes()):
        return False
    if element.OwnerViewId != DB.ElementId.InvalidElementId:
        return False
    return element.get_BoundingBox(None) is not None


def is_excluded_class(element):
    """Views (incl. sheets, cameras), link instances, CAD imports, groups."""
    return isinstance(element, (DB.View, DB.RevitLinkInstance,
                                DB.ImportInstance, DB.Group))


def is_model_category(element):
    """True if the element has a Model-type category. Raises on read failure."""
    category = element.Category
    return category is not None and category.CategoryType == DB.CategoryType.Model


def flag_info(element):
    """(in_design_option, demolished) for information only. Nothing is
    excluded because of these. Raises on read failure."""
    in_option = element.DesignOption is not None
    demolished = element.DemolishedPhaseId != DB.ElementId.InvalidElementId
    return in_option, demolished


def type_name(doc, element):
    """Type name read from the type's SYMBOL_NAME_PARAM, not Element.Name
    (Element.Name raises AttributeError on some elements in IronPython)."""
    try:
        type_el = doc.GetElement(element.GetTypeId())
        param = type_el.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
        return param.AsString() or "-"
    except Exception:
        return "-"


def level_name(doc, element):
    """Level via LevelId, falling back to Reference Level, then Schedule
    Level instance parameters. '-' if none."""
    try:
        candidates = [element.LevelId]
        for bip in (DB.BuiltInParameter.INSTANCE_REFERENCE_LEVEL_PARAM,
                    DB.BuiltInParameter.SCHEDULE_LEVEL_PARAM):
            param = element.get_Parameter(bip)
            if param is not None and param.HasValue:
                candidates.append(param.AsElementId())
        for level_id in candidates:
            if level_id is not None and level_id != DB.ElementId.InvalidElementId:
                level = doc.GetElement(level_id)
                if level is not None:
                    return level.Name
    except Exception:
        pass
    return "-"


class Result(object):
    def __init__(self):
        self.stats = {}      # category -> [checked, empty, no_param, errors, excluded]
        self.missing = {}    # category -> [elements]
        self.errors = []     # (element id, message), capped
        self.error_total = 0
        self.cat_errors = 0  # category unreadable; part of error_total, not of 'seen'
        self.in_option = 0   # checked-or-not elements in design options
        self.demolished = 0
        self.seen = 0        # elements looked at (passed the geometry/view filter)
        self.place_errors = 0  # could not apply the geometry filter; part of error_total
        self.not_placed = 0  # excluded by the geometry/view filter
        self.cancelled = False


def record_error(result, element, exc):
    result.error_total += 1
    if len(result.errors) < MAX_ERROR_ROWS:
        try:
            eid = element.Id
        except Exception:
            eid = None
        result.errors.append((eid, str(exc)))


def process(element, result):
    """Classify one element into result. Never lets one bad element stop the
    scan; read failures go to the error count."""
    cat_name = UNKNOWN_CATEGORY
    try:
        if is_excluded_class(element):
            return
        if not is_model_category(element):
            return
        cat_name = element.Category.Name
    except Exception as exc:
        # Cannot tell whether it is a model element: count it as an error.
        row = result.stats.setdefault(UNKNOWN_CATEGORY, [0, 0, 0, 0, 0])
        row[3] += 1
        result.cat_errors += 1
        record_error(result, element, exc)
        return
    row = result.stats.setdefault(cat_name, [0, 0, 0, 0, 0])
    try:
        passes = passes_geometry_filter(element)
    except Exception as exc:
        row[3] += 1
        result.place_errors += 1
        record_error(result, element, exc)
        return
    if not passes:
        row[4] += 1
        result.not_placed += 1
        return
    result.seen += 1
    try:
        in_option, demolished = flag_info(element)
        if in_option:
            result.in_option += 1
        if demolished:
            result.demolished += 1
    except Exception:
        pass  # information only; the Mark check below still runs
    try:
        state = mark_state(element)
    except Exception as exc:
        row[3] += 1
        record_error(result, element, exc)
        return
    if state == "none":
        row[2] += 1
        return
    row[0] += 1
    if state == "missing":
        row[1] += 1
        result.missing.setdefault(cat_name, []).append(element)


def scan(doc, progress=None):
    """progress: optional object with update_progress(done, total) and a
    cancelled attribute. Returns a Result (partial if cancelled)."""
    result = Result()
    collector = DB.FilteredElementCollector(doc).WhereElementIsNotElementType()
    total = collector.GetElementCount()
    done = 0
    for element in collector:
        process(element, result)
        done += 1
        if progress is not None and done % PROGRESS_STEP == 0:
            if progress.cancelled:
                result.cancelled = True
                break
            progress.update_progress(done, total)
    return result


def report(doc, result, output):
    stats = result.stats
    checked = sum(r[0] for r in stats.values())
    empty = sum(r[1] for r in stats.values())
    no_param = sum(r[2] for r in stats.values())
    output.print_md("# Missing Mark check")
    output.print_md("Model: **{}**. Active project only, linked models not "
                    "checked. All phases and all design options are included "
                    "(demolished elements too).".format(doc.Title))
    if result.cancelled:
        output.print_md("**Cancelled: this is a PARTIAL result.** Only the "
                        "elements scanned before cancel are counted.")
    if checked == 0:
        if result.error_total or result.cancelled:
            output.print_md("**No elements were successfully checked.** See the "
                            "read errors and any partial-result warning; the "
                            "model may still have elements with a Mark parameter.")
        else:
            output.print_md("**Nothing was checked:** no model elements with a "
                            "Mark parameter were found.")
    else:
        output.print_md("**{} of {} elements with a Mark parameter have an empty Mark.**"
                        .format(empty, checked))
    mark_errors = result.error_total - result.cat_errors - result.place_errors
    output.print_md("{} elements looked at (passed the geometry/view filter): {} with a Mark parameter "
                    "checked, {} without one (not checked), {} where reading "
                    "the Mark failed. Of those looked at, {} are in design "
                    "options and {} are demolished (included in the counts)."
                    .format(result.seen, checked, no_param, mark_errors,
                            result.in_option, result.demolished))
    output.print_md("Excluded by the geometry/view filter: **{}** elements in "
                    "Model-type categories with no model bounding box, or "
                    "view-specific, or a project base point or internal "
                    "origin. Examples: materials, legend components. They are "
                    "counted per category in the last column and not checked. "
                    "This filter is a heuristic: it does not guarantee that "
                    "every real model element is covered."
                    .format(result.not_placed))
    if result.cat_errors or result.place_errors:
        output.print_md("Also not counted above: **{}** elements whose category "
                        "could not be read and **{}** where it could not be "
                        "determined whether they pass the geometry/view filter. See the read "
                        "errors below.".format(result.cat_errors, result.place_errors))
    rows = [[cat, r[0], r[1], r[2], r[3], r[4]] for cat, r in sorted(stats.items())]
    if rows:
        output.print_table(table_data=rows, columns=[
            "Category", "Checked (has Mark parameter)", "Empty Mark",
            "No Mark parameter (not checked)", "Read errors",
            "Excluded: no model geometry or view-specific (not checked)"])
    if result.error_total:
        output.print_md("## Read errors: {}".format(result.error_total))
        err_rows = [[output.linkify(eid) if eid is not None else "-", msg]
                    for eid, msg in result.errors]
        output.print_table(table_data=err_rows, columns=["Element", "Error"])
        if result.error_total > len(result.errors):
            output.print_md("Showing the first {} of {} errors.".format(
                len(result.errors), result.error_total))
    for cat in sorted(result.missing):
        elements = sorted(result.missing[cat], key=lambda x: id_value(x.Id))
        output.print_md("## {}: {} without a Mark".format(cat, len(elements)))
        shown = elements[:MAX_ROWS_PER_CATEGORY]
        table = [[output.linkify(e.Id), type_name(doc, e), level_name(doc, e)]
                 for e in shown]
        output.print_table(table_data=table,
                           columns=["Element (click to select)", "Type", "Level"])
        if len(elements) > len(shown):
            output.print_md("Showing the first {} of {}. The summary table "
                            "above has the full count.".format(len(shown), len(elements)))


def main():
    doc = revit.doc
    if doc is None:
        forms.alert("Open a project first.", exitscript=True)
    if doc.IsFamilyDocument:
        forms.alert("This check works on project files, not family files.",
                    exitscript=True)
    output = script.get_output()
    with forms.ProgressBar(title="Checking Mark ({value} of {max_value})",
                           cancellable=True) as pb:
        result = scan(doc, pb)
    report(doc, result, output)


if __name__ == "__main__":
    main()
