# -*- coding: utf-8 -*-
"""Find structural columns and beams with an empty Mark.

Read only. It opens no transaction and changes nothing in the model.
Scope: the active project document only (linked models are not checked).
Columns: Structural Columns category.
Beams: Structural Framing category, family instances whose StructuralType is
Beam. Braces and other framing types are left out.
"""
from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB.Structure import StructuralType


def id_value(element_id):
    """ElementId as an integer. Value exists from Revit 2024; IntegerValue was
    removed in Revit 2026 and is the only option before 2024."""
    if hasattr(element_id, "Value"):
        return element_id.Value
    return element_id.IntegerValue


def mark_is_missing(element):
    """True if the element's Mark is absent or blank.

    Mark is the built-in instance parameter ALL_MODEL_MARK. If the element
    has no such parameter at all, it counts as missing too.
    """
    param = element.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
    if param is None or not param.HasValue:
        return True
    value = param.AsString()
    return value is None or value.strip() == ""


def is_beam(element):
    return (isinstance(element, DB.FamilyInstance)
            and element.StructuralType == StructuralType.Beam)


def collect(doc, category, keep=None):
    collector = (DB.FilteredElementCollector(doc)
                 .OfCategory(category)
                 .WhereElementIsNotElementType())
    return [e for e in collector if keep is None or keep(e)]


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
    """Level via LevelId; beams often have an invalid LevelId, so fall back to
    the Reference Level, then the Schedule Level, instance parameters."""
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
    return "-"


def main():
    doc = revit.doc
    if doc is None:
        forms.alert("Open a project first.", exitscript=True)
    if doc.IsFamilyDocument:
        forms.alert("This check works on project files, not family files.",
                    exitscript=True)
    output = script.get_output()
    groups = [
        ("Structural Columns", collect(doc, DB.BuiltInCategory.OST_StructuralColumns)),
        ("Beams (Structural Framing with type Beam)",
         collect(doc, DB.BuiltInCategory.OST_StructuralFraming, is_beam)),
    ]
    output.print_md("# Missing Mark check")
    output.print_md("Model: **{}**. Active model only, linked models not checked."
                    .format(doc.Title))
    total = 0
    checked = 0
    for label, elements in groups:
        missing = [e for e in elements if mark_is_missing(e)]
        total += len(missing)
        checked += len(elements)
        output.print_md("## {}: {} of {} without a Mark"
                        .format(label, len(missing), len(elements)))
        if missing:
            rows = [[output.linkify(e.Id), type_name(doc, e), level_name(doc, e)]
                    for e in sorted(missing, key=lambda x: id_value(x.Id))]
            output.print_table(table_data=rows,
                               columns=["Element (click to select)", "Type", "Level"])
    if checked == 0:
        output.print_md("**Nothing was checked:** no structural columns or beams "
                        "were found in this model.")
    elif total == 0:
        output.print_md("All {} checked columns and beams have a Mark.".format(checked))


if __name__ == "__main__":
    main()
