"""CAD drawings and solids (.dwg .dxf .step .iges .ifc .fcstd .3dm .skp .dgn), capped at 10,000 files so the rest
of the Drive goes to 3D models. Curated part libraries and sample sets first, then the most-starred GitHub
repositories for CAD topics."""
from urllib.parse import quote

from .common import get, safe
from .util import CAD, gh, gh_file, gh_search, gh_tree

LIMIT = 10_000
FOLDER = {"dwg": "DWG", "dxf": "DXF", "step": "STEP", "stp": "STEP", "iges": "IGES", "igs": "IGES", "ifc": "IFC",
          "fcstd": "FreeCAD", "3dm": "Rhino 3DM", "skp": "SketchUp", "dgn": "DGN", "sat": "ACIS SAT"}
CAP = 80 * 2 ** 20

CURATED = {  # repository: collection
    "FreeCAD/FreeCAD-library": "FreeCAD parts library",
    "ezdxf/ezdxf": "ezdxf samples",
    "LibreCAD/LibreCAD": "LibreCAD",
    "buildingSMART/Sample-Test-Files": "buildingSMART samples",
    "buildingSMART/IFC4.3.x-sample-models": "IFC 4.3 infrastructure samples",
    "IfcOpenShell/files": "IfcOpenShell samples",
    "opensourceBIM/TestFiles": "BIMserver test files",
    "youshengCode/IfcSampleFiles": "IFC sample files",
    "jscad/OpenJSCAD.org": "JSCAD",
    "openscad/openscad": "OpenSCAD",
}
TOPICS = ["dxf", "dwg", "dxf-files", "dwg-files", "autocad", "cad-drawings", "cad-blocks", "step-files",
          "cad-models", "freecad-models", "freecad", "ifc", "ifc-files", "bim-models", "rhino3d", "sketchup",
          "mechanical-design", "cnc", "laser-cutting", "pcb-design", "cad"]


def _ext(p):
    n = p.rsplit("/", 1)[-1]
    return n.rsplit(".", 1)[-1].lower() if "." in n else ""


def _repo(s, sink, st, repo, branch, coll):
    files = [f for f in gh_tree(s, repo, branch) if _ext(f["path"]) in FOLDER and f.get("size", 0) <= CAP]
    n = 0
    for f in files:
        if st["cad_count"] >= LIMIT or sink.full():
            break
        if gh_file(s, sink, repo, branch, quote(f["path"]),
                   f"{CAD}/{FOLDER[_ext(f['path'])]}/{coll}/{f['path']}", CAP):
            st["cad_count"] += 1
            n += 1
    return n


def cad(sink, st):
    s = gh()
    st.setdefault("cad_count", 0)
    done = st.setdefault("cad_repos", [])
    n = 0
    for repo, coll in CURATED.items():
        if st["cad_count"] >= LIMIT or sink.full():
            return n
        if repo in done:
            continue
        r = get(s, f"https://api.github.com/repos/{repo}")
        if r:
            n += _repo(s, sink, st, repo, r.json()["default_branch"], coll)
        if not sink.full():
            done.append(repo)
    pages = st.setdefault("cad_page", {})
    for t in TOPICS:
        if st["cad_count"] >= LIMIT or sink.full():
            return n
        page = pages.get(t, 1)
        if page > 10:
            continue
        pages[t] = page + 1
        for item in gh_search(s, f"topic:{t} archived:false fork:false", page):
            if st["cad_count"] >= LIMIT or sink.full():
                return n
            name = item["full_name"]
            if name in done:
                continue
            n += _repo(s, sink, st, name, item["default_branch"], safe(item["name"], 60))
            done.append(name)
    return n


SOURCES = {"cad": cad}
