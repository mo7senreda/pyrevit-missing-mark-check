# Logic test with stand-in objects. It does NOT run Revit or the Revit API.
import sys, types

class P(object):
    def __init__(s, has, val): s.HasValue, s._v = has, val
    def AsString(s): return s._v
class Boom(Exception): pass
class E(object):
    def __init__(s, p=None, cat="ok", dopt=None, dem=None, fail=False, name="Cat", bbox=True, owner=None, bbfail=False):
        s.p, s._cat, s.DesignOption, s.DemolishedPhaseId = p, cat, dopt, dem
        s.fail, s.name, s.Id = fail, name, 1
        s.bbox, s.bbfail = bbox, bbfail
        s.OwnerViewId = owner if owner is not None else Id(-1)
    def get_BoundingBox(s, v):
        if s.bbfail: raise Boom("bbox")
        return object() if s.bbox else None
    @property
    def Category(s):
        if s._cat == "boom": raise Boom("category")
        if s._cat is None: return None
        return types.SimpleNamespace(CategoryType=("Model" if s._cat == "ok" else "Annotation"), Name=s.name)
    def get_Parameter(s, bip):
        if s.fail: raise Boom("param")
        return s.p
class Id(object):
    def __init__(s, v): s.Value = v
    def __eq__(s, o): return isinstance(o, Id) and s.Value == o.Value
    def __ne__(s, o): return not s == o
class View(E): pass
class Link(E): pass
class Imp(E): pass
class Grp(E): pass
class Base(E): pass

db = types.SimpleNamespace(
    BuiltInParameter=types.SimpleNamespace(ALL_MODEL_MARK=1),
    CategoryType=types.SimpleNamespace(Model="Model", Annotation="Annotation"),
    ElementId=types.SimpleNamespace(InvalidElementId=Id(-1)),
    View=View, RevitLinkInstance=Link, ImportInstance=Imp, Group=Grp, BasePoint=Base)
pr = types.ModuleType("pyrevit"); pr.revit = None; pr.DB = db; pr.script = None; pr.forms = None
sys.modules["pyrevit"] = pr
src = open("MarkCheck.extension/BIM.tab/Checks.panel/MissingMark.pushbutton/script.py").read()
ns = {}
exec(compile(src, "script.py", "exec"), ns)

ms = ns["mark_state"]
assert ms(E(None)) == "none"
assert ms(E(P(False, None))) == "missing"
assert ms(E(P(True, ""))) == "missing"
assert ms(E(P(True, "   "))) == "missing"
assert ms(E(P(True, None))) == "missing"
assert ms(E(P(True, "C1"))) == "ok"
try:
    ms(E(fail=True)); assert False
except Boom:
    pass  # a read failure is raised, not turned into missing/none

def run(elements):
    r = ns["Result"]()
    for e in elements: ns["process"](e, r)
    return r

dem = Id(-1)
els = [
    E(P(True, "A"), dem=dem, name="Walls"),            # ok
    E(P(True, ""), dem=dem, name="Walls"),             # empty
    E(None, dem=dem, name="Rooms"),                    # no Mark parameter
    E(P(True, ""), dopt=object(), dem=dem, name="Walls"),   # design option: still counted
    E(P(True, ""), dem=Id(5), name="Walls"),           # demolished: still counted
    E(P(True, ""), cat="ann", name="Tags"),            # annotation: not a model element
    E(P(True, ""), cat=None),                          # no category
    View(P(True, ""), dem=dem), Link(P(True, ""), dem=dem),
    Imp(P(True, ""), dem=dem), Grp(P(True, ""), dem=dem),   # excluded classes
    E(fail=True, dem=dem, name="Walls"),               # parameter read failure
    E(cat="boom"),                                     # category read failure
    E(P(True, ""), dem=dem, name="Materials", bbox=False),            # definition: no geometry
    E(P(True, ""), dem=dem, name="Legend Components", owner=Id(77)),  # view-specific
    Base(P(True, ""), dem=dem, name="Project Base Point"),            # reference point
    E(P(True, ""), dem=dem, name="Walls", bbfail=True),               # placement unreadable
]
r = run(els)
assert r.stats["Walls"] == [4, 3, 0, 2, 0], r.stats["Walls"]   # checked, empty, no-param, errors, not placed
assert r.stats["Rooms"] == [0, 0, 1, 0, 0]
assert r.stats["Materials"] == [0, 0, 0, 0, 1]
assert r.stats["Legend Components"] == [0, 0, 0, 0, 1]
assert r.stats["Project Base Point"] == [0, 0, 0, 0, 1]
assert "Tags" not in r.stats
assert r.stats[ns["UNKNOWN_CATEGORY"]] == [0, 0, 0, 1, 0]
assert r.error_total == 3 and r.cat_errors == 1 and r.place_errors == 1, (r.error_total, r.cat_errors, r.place_errors)
assert r.seen == 6 and r.not_placed == 3, (r.seen, r.not_placed)
# reconciliation: looked at = checked + no-param + mark read errors
checked = sum(v[0] for v in r.stats.values()); nop = sum(v[2] for v in r.stats.values())
assert r.seen == checked + nop + (r.error_total - r.cat_errors - r.place_errors)
assert r.in_option == 1 and r.demolished == 1
assert len(r.missing["Walls"]) == 3
assert "Materials" not in r.missing   # 191 material "empty marks" must not be reported

class V(object): Value = 5
class I(object): IntegerValue = 7
assert ns["id_value"](V()) == 5 and ns["id_value"](I()) == 7

class Prog(object):
    cancelled = False
    def update_progress(s, d, t): pass
print("ok: mark_state, scope, error counting, no design-option/demolished exclusion")
