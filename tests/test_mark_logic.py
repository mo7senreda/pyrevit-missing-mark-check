# Logic test with stand-in objects. It does NOT run Revit or the Revit API.
import sys, types

class P(object):
    def __init__(s, has, val): s.HasValue, s._v = has, val
    def AsString(s): return s._v
class E(object):
    def __init__(s, p): s.p = p
    def get_Parameter(s, bip): return s.p

# stub the modules the script imports
db = types.SimpleNamespace(BuiltInParameter=types.SimpleNamespace(ALL_MODEL_MARK=1),
    BuiltInCategory=types.SimpleNamespace(OST_StructuralColumns=2, OST_StructuralFraming=3))
class FI(object): pass
db.FamilyInstance = FI
pr = types.ModuleType("pyrevit"); pr.revit = None; pr.DB = db; pr.script = None; pr.forms = None
sys.modules["pyrevit"] = pr
st = types.ModuleType("Autodesk.Revit.DB.Structure"); st.StructuralType = types.SimpleNamespace(Beam=1, Brace=2)
for n in ("Autodesk","Autodesk.Revit","Autodesk.Revit.DB"): sys.modules[n]=types.ModuleType(n)
sys.modules["Autodesk.Revit.DB.Structure"] = st
src = open("MarkCheck.extension/BIM.tab/Checks.panel/MissingMark.pushbutton/script.py").read()
ns = {}
exec(compile(src, "script.py", "exec"), ns)
f = ns["mark_is_missing"]
assert f(E(None))
assert f(E(P(False, None)))
assert f(E(P(True, "")))
assert f(E(P(True, "   ")))
assert f(E(P(True, None)))
assert not f(E(P(True, "C1")))
b=FI(); b.StructuralType=1
r=FI(); r.StructuralType=2
assert ns["is_beam"](b) and not ns["is_beam"](r) and not ns["is_beam"](object())
class V(object): Value=5
class I(object): IntegerValue=7
assert ns["id_value"](V())==5 and ns["id_value"](I())==7
print("ok: mark, beam filter, id_value")
