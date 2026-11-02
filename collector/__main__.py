"""python -m collector --sources sketchfab,images,... --state state/x.json --live

Writes into OUT and moves files to the rclone remote as it goes; run state stays in STATE (kept between runs
in the Actions cache, never on Drive). Logs show counts only."""
import argparse
import os
import time
import traceback

from . import adobe, boxmodels, brex, cad, docs, focus, images, models, sheets, zoom
from .common import Sink, State

SOURCES = {**adobe.SOURCES, **docs.SOURCES, **boxmodels.SOURCES, **models.SOURCES, **cad.SOURCES, **images.SOURCES, **focus.SOURCES, **sheets.SOURCES, **brex.SOURCES, **zoom.SOURCES}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default=",".join(SOURCES))
    ap.add_argument("--out", default="out")
    ap.add_argument("--state", default="state/state.json")
    ap.add_argument("--remote", default=os.environ.get("REMOTE", "pax:Asset Library"))
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--keep", action="store_true", help="dry run: keep files in OUT for inspection")
    ap.add_argument("--budget-gb", type=float, default=20)
    ap.add_argument("--minutes", type=float, default=320)
    a = ap.parse_args()
    st = State(a.state)
    sink = Sink(a.out, a.remote, a.live, st, int(a.budget_gb * 2 ** 30), time.time() + a.minutes * 60, a.keep)
    srcs = [x.strip() for x in a.sources.split(",") if x.strip()]
    failed = []
    for i, name in enumerate(srcs):
        left = sink.deadline - time.time()  # fair share of the time left
        sink.slice_end = time.time() + max(5 * 60, left / (len(srcs) - i))
        if sink.full():
            print(f"{name}: skipped (time or size budget reached)")
            continue
        t0 = time.time()
        try:
            n = SOURCES[name](sink, st.section(name))
            sink.flush()
            print(f"{name}: {n} items in {time.time() - t0:.0f}s; total {sink.files} files, "
                  f"{sink.sent_bytes / 2 ** 20:.0f} MB")
        except Exception:
            failed.append(name)
            print(f"{name}: FAILED")
            traceback.print_exc()
            try:
                sink.flush()
            except Exception:
                traceback.print_exc()
    print(f"done: {sink.files} files, {sink.sent_bytes / 2 ** 30:.2f} GB, live={a.live}")
    if failed:
        raise SystemExit(f"failed sources: {', '.join(failed)}")


if __name__ == "__main__":
    main()
