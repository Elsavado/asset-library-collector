"""python -m studio --root <page id> [--minutes N] [--dry] : build the Halcyon Vertex Studio workspace in Notion."""
import argparse
import os
import time

from .build import Builder, Notion, OutOfTime, State


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("NOTION_ROOT", "40da22cfdc4d80fcbccde2c28a42e0c8"))
    ap.add_argument("--state", default="state/notion.json")
    ap.add_argument("--minutes", type=float, default=300)
    ap.add_argument("--scale", type=float, default=1.0, help="row volume multiplier")
    ap.add_argument("--dry", action="store_true", help="generate every payload without calling Notion")
    a = ap.parse_args()
    st = State(a.state if not a.dry else a.state + ".dry")
    if st.data.get("complete"):
        print("workspace already complete; nothing to do")
        return
    n = Notion(os.environ.get("NOTION_TOKEN", ""), dry=a.dry)
    b = Builder(n, st, a.root, time.time() + a.minutes * 60, a.scale)
    t0 = time.time()
    try:
        b.run()
        print("COMPLETE")
    except OutOfTime:
        print("time budget reached; resuming next run")
    finally:
        st.save()
        print(f"created this run: {b.summary() or 'nothing'}; API calls {n.calls}; total objects "
              f"{len(st.data['ids'])}; {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
