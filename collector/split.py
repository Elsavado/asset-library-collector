"""Which Drive owns an item that more than one collector can reach (user rule 2026-11-04: never the same content on
two Drives). The SAME file sits in three collectors -- asset-library-collector (salvadorsekwa, "assets"),
construction-ops-collector (Lintel, "construction") and mobility-ops-collector ("mobility") -- so every collector
takes the same decision and the three Drives stay disjoint. Keep the copies identical.

  Objaverse 1.0 object   mobility      if it is a road vehicle or road furniture (name / tags / category)
                         construction  else if it is in the LVIS-annotated set or describes a building, house,
                                       interior or construction scene
                         assets        everything else (~750k objects)
  Building / architecture image (Commons, Openverse, Pixabay, Unsplash, Pexels): split by its source id
                         (half each between construction and assets); car images are assets only; images whose title
                         names a road sign or traffic light are mobility's
  GitHub repository      construction  if its name says BIM / IFC / Revit / architecture / building /
                                       construction, or one in four of the rest (CAD included, by hash); assets
                                       otherwise
  Curated sample sets and Poly Haven: listed in SHARED_REPOS / POLYHAVEN_OWNER
"""
import hashlib
import re

VEHICLE = re.compile(r"\b(car|cars|truck|lorry|pickup|bus|van|suv|sedan|coupe|hatchback|jeep|taxi|limo|limousine|"
                     r"tractor|trailer|semi|forklift|motorcycle|motorbike|scooter|moped|bicycle|bike|ambulance|"
                     r"fire ?truck|police car|tow truck|excavator|bulldozer|dump truck|garbage truck|tram|trolley|"
                     r"vehicle|automobile|racecar|race car|go-?kart|rover|wheel|tire|tyre|engine|chassis)\b", re.I)
ROADWORDS = re.compile(r"\b(road|street|highway|freeway|motorway|intersection|crossroad|roundabout|crosswalk|"
                       r"traffic ?light|traffic ?signal|stop ?sign|road ?sign|traffic ?sign|traffic ?cone|"
                       r"barrier|barricade|guard ?rail|bollard|street ?light|lamp ?post|parking|garage|gas station|"
                       r"petrol station|bridge|tunnel|toll|sidewalk|curb|kerb|manhole|road ?block|detour|"
                       r"road ?closed|road ?works|construction sign)\b", re.I)
NOT_ROAD = re.compile(r"\b(plane|aircraft|airplane|jet|helicopter|ship|boat|yacht|submarine|spaceship|spacecraft|"
                      r"starship|rocket|tank|gun|rifle|weapon|sword|mech|robot|character|girl|boy|anime|cartoon "
                      r"character|toy car)\b", re.I)
ARCHITECTURE = re.compile(
    r"futuris.*(building|house|tower|city)|sci-?fi.*(building|house|base|station|city)|space ?station|"
    r"space ?colony|mars base|moon base|lunar base|arcology|parametric (architecture|building|facade|pavilion)|"
    r"modern (house|home|villa|cabin|residence)|contemporary (house|home|villa)|minimalist (house|home)|villa|"
    r"tiny ?house|container ?(house|home)|prefab(ricated)? (house|home|building)|modular (house|home|building)|"
    r"passive ?house|smart ?home|eco ?(house|home)|3d.?printed (house|home|building)|mansion|bungalow|log cabin|"
    r"chalet|townhouse|duplex|beach house|lake house|skyscraper|high-?rise|tower block|office tower|"
    r"office building|commercial building|apartment|condo|residential building|city block|downtown|cityscape|"
    r"city scene|\bconstruction\b|scaffold|excavator|bulldozer|tower crane|crane truck|concrete mixer|rebar|"
    r"building site|backhoe|steel frame|formwork|interior|living ?room|kitchen|bedroom|bathroom|lobby|"
    r"office space|house|home|cottage|farmhouse|cabin|architect|archviz|facade|pavilion|building|stadium|museum|"
    r"airport|train station|bridge|cathedral|church|temple|castle", re.I)
SIGN_IMAGE = re.compile(r"\b(road ?sign|traffic ?sign|stop ?sign|street ?sign|traffic ?light|traffic ?signal|"
                        r"signpost|sign ?post|speed limit|yield sign|warning sign|give way)\b", re.I)
CONSTRUCTION_REPO = re.compile(r"(?<![a-z])(bim|ifc)(?![a-z])|revit|archicad|architect|building|construct|"
                               r"civil|structural|sketchup|grasshopper", re.I)

SHARED_REPOS = {  # curated sets that both the Asset Library and Lintel used to download: one owner each
    "nasa/NASA-3D-Resources": "assets", "KhronosGroup/glTF-Sample-Assets": "assets",
    "KhronosGroup/glTF-Sample-Models": "assets", "alecjacobson/common-3d-test-models": "assets",
    "mikedh/trimesh": "assets",
}
POLYHAVEN_OWNER = "assets"


def _bucket(key, n):
    return int(hashlib.sha1(key.encode("utf-8", "surrogateescape")).hexdigest()[:8], 16) % n


def objaverse_owner(uid, md, lvis=frozenset()):
    """md: the object's Objaverse metadata (name, tags, categories); lvis: uids of the LVIS-annotated set."""
    md = md or {}
    name = md.get("name") or ""
    tags = " ".join(t.get("name", "") for t in md.get("tags") or [] if isinstance(t, dict))
    cats = [c.get("name", "") for c in md.get("categories") or [] if isinstance(c, dict)]
    text = f"{name} {tags}"
    is_vehicle = bool(VEHICLE.search(name) or "cars-vehicles" in cats and VEHICLE.search(text))
    if (is_vehicle or ROADWORDS.search(text)) and not NOT_ROAD.search(text):
        return "mobility"
    if uid in lvis or ARCHITECTURE.search(text):
        return "construction"
    return "assets"


def building_image_owner(source, ident, title=""):
    """A building / architecture image from a shared source: half each, by its id at that source."""
    if SIGN_IMAGE.search(title or ""):
        return "mobility"
    return "construction" if _bucket(f"{source}:{ident}", 2) == 0 else "assets"


def image_owner(source, ident, title="", theme=""):
    """Any image from a shared source: road signs -> mobility; buildings split; everything else -> assets."""
    if SIGN_IMAGE.search(title or ""):
        return "mobility"
    if theme.lower().startswith(("building", "architecture")):
        return building_image_owner(source, ident, title)
    return "assets"


def repo_owner(full_name):
    if full_name in SHARED_REPOS:
        return SHARED_REPOS[full_name]
    if CONSTRUCTION_REPO.search(full_name):
        return "construction"
    return "construction" if _bucket(full_name.lower(), 4) == 0 else "assets"
