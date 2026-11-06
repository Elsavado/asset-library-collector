"""30 Zoom calls: 15 real public meetings held on Zoom (city councils, boards, commissions; Internet Archive) with
transcripts, and 15 generated calls of a fictional company in Zoom cloud-recording form (gallery-view MP4,
audio M4A, transcript VTT, chat TXT, participants CSV). Generated speech uses Piper voices."""
import csv
import io
import json
import os
import random
import shutil
import subprocess
import tempfile
import wave
from datetime import datetime, timedelta

from .common import get, safe, session
from .util import ZOOM, download

REAL, MADE = 30, 0  # 2026-11-07: generated calls deleted, real public meetings only
IA = "https://archive.org"


# ---- real public meetings -------------------------------------------------------------------------------
QUERY = ('(title:(zoom) OR description:("zoom meeting")) AND mediatype:movies AND '
         '(title:(council OR board OR commission OR committee OR "town meeting" OR "public hearing")) '
         'AND (language:eng OR language:English OR language:en)')


def _vtt_time(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def _transcribe(media, out_vtt):
    """English transcript with timestamps (faster-whisper, CPU)."""
    from faster_whisper import WhisperModel
    model = WhisperModel("base.en", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(media, language="en", vad_filter=True)
    with open(out_vtt, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for i, sgm in enumerate(segs, 1):
            f.write(f"{i}\n{_vtt_time(sgm.start)} --> {_vtt_time(sgm.end)}\n{sgm.text.strip()}\n\n")


def real(sink, st):
    s = session()
    done = st.setdefault("zoom_real", [])
    n = 0
    page = st.get("zoom_page", 1)
    while len(done) < REAL and not sink.full() and page <= 20:
        r = get(s, f"{IA}/advancedsearch.php", params={"q": QUERY, "fl[]": "identifier,title", "rows": 50,
                                                       "page": page, "sort[]": "downloads desc", "output": "json"})
        docs = ((r.json().get("response") or {}).get("docs") or []) if r else []
        page += 1
        st["zoom_page"] = page
        if not docs:
            break
        for d in docs:
            if len(done) >= REAL or sink.full():
                break
            ident = d["identifier"]
            if ident in done or ident in st.setdefault("zoom_skip", []):
                continue
            m = get(s, f"{IA}/metadata/{ident}")
            files = (m.json().get("files") or []) if m else []
            meta = (m.json().get("metadata") or {}) if m else {}
            vids = [f for f in files if f["name"].lower().endswith(".mp4") and 20 * 2 ** 20 < int(f.get("size") or 0)
                    < 1500 * 2 ** 20 and 600 < float(f.get("length") or 0) < 3 * 3600]
            if not vids:
                st["zoom_skip"].append(ident)
                continue
            v = min(vids, key=lambda f: int(f["size"]))
            title = safe(d.get("title") or ident, 90)
            date = (meta.get("date") or "")[:10]
            base = f"{ZOOM}/Public Meetings/{(date + ' ') if date else ''}{title}"
            if not download(s, f"{IA}/download/{ident}/{v['name']}", 1600 * 2 ** 20, sink, f"{base}/{title}.mp4"):
                continue
            subs = [f for f in files if f["name"].lower().endswith((".srt", ".vtt"))]
            if subs:
                download(s, f"{IA}/download/{ident}/{subs[0]['name']}", 20 * 2 ** 20, sink,
                         f"{base}/{title} transcript.{subs[0]['name'].rsplit('.', 1)[-1].lower()}")
            else:
                vtt = sink.path(f"{base}/{title} transcript.vtt")
                try:
                    _transcribe(sink.path(f"{base}/{title}.mp4"), vtt)
                    sink.wrote(vtt)
                except Exception:
                    if os.path.exists(vtt):
                        os.remove(vtt)
            desc = meta.get("description")
            if isinstance(desc, list):
                desc = "\n".join(desc)
            if desc:
                sink.write_text(f"{base}/{title} agenda and notes.txt", _strip_html(desc))
            done.append(ident)
            n += 1
    return n


def _strip_html(t):
    import re
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"<[^>]+>", "\n", t)).strip()


# ---- generated company calls ----------------------------------------------------------------------------
COMPANY = "Brightmoor Analytics"
DOMAIN = "brightmooranalytics.example"
PEOPLE = [  # name, title, voice
    ("Dana Whitlock", "CEO", "en_US-lessac-medium"), ("Mateo Quintero", "CFO", "en_US-ryan-medium"),
    ("Priya Banerjee", "VP Engineering", "en_US-amy-medium"), ("Elliot Marlowe", "Head of Sales", "en_US-joe-medium"),
    ("Hana Fujimoto", "Product Manager", "en_US-kristin-medium"), ("Kofi Okafor", "Staff Engineer", "en_GB-alan-medium"),
    ("Sofia Lindqvist", "Head of Marketing", "en_GB-jenny_dioco-medium"), ("Ravi Haddad", "Controller", "en_US-hfc_male-medium"),
    ("Leilani Gallagher", "Customer Success Lead", "en_US-hfc_female-medium"), ("Tomas Kowalski", "SRE Lead", "en_US-ryan-medium"),
    ("Ines Delacroix", "People Partner", "en_GB-jenny_dioco-medium"), ("Jae Iverson", "Designer", "en_US-kristin-medium"),
]
VOICE_PATH = {"en_US-lessac-medium": "en/en_US/lessac/medium", "en_US-ryan-medium": "en/en_US/ryan/medium",
              "en_US-amy-medium": "en/en_US/amy/medium", "en_US-joe-medium": "en/en_US/joe/medium",
              "en_US-kristin-medium": "en/en_US/kristin/medium", "en_GB-alan-medium": "en/en_GB/alan/medium",
              "en_GB-jenny_dioco-medium": "en/en_GB/jenny_dioco/medium",
              "en_US-hfc_male-medium": "en/en_US/hfc_male/medium", "en_US-hfc_female-medium": "en/en_US/hfc_female/medium"}


def _meetings():
    """15 meetings: (title, host index, attendee indexes, script builder)."""
    return [
        ("Weekly Leadership Sync", 0, [0, 1, 2, 3, 6], _leadership),
        ("Q3 Financial Review", 1, [1, 0, 7, 3], _finance),
        ("Sprint 42 Planning", 4, [4, 2, 5, 9, 11], _sprint),
        ("Incident Postmortem - API Latency", 9, [9, 5, 2, 8], _postmortem),
        ("Pipeline Review", 3, [3, 0, 8, 6], _pipeline),
        ("Month-End Close Check-in", 7, [7, 1], _close),
        ("Product Design Review - Usage Dashboard", 11, [11, 4, 5, 8], _design),
        ("Customer Onboarding - Fernhill Logistics", 8, [8, 4, 5], _onboarding),
        ("Marketing Campaign Planning", 6, [6, 3, 4, 0], _marketing),
        ("Engineering All-Hands", 2, [2, 5, 9, 11, 4], _eng_allhands),
        ("Budget Planning FY2027", 1, [1, 0, 2, 3, 6, 7], _budget),
        ("Hiring Debrief - Senior Backend Engineer", 10, [10, 2, 5, 9], _hiring),
        ("Sprint 42 Retrospective", 4, [4, 2, 5, 9, 11], _retro),
        ("Quarterly Business Review - Tidewater Health", 8, [8, 3, 4, 0], _qbr),
        ("Security and Compliance Update", 9, [9, 2, 1, 10], _security),
    ]


def _say(rnd, lines):
    return rnd.choice(lines) if isinstance(lines, list) else lines


def _open(rnd, host, people, title):
    h = PEOPLE[host][0].split()[0]
    lines = [(host, f"Hi everyone, thanks for joining. This is the {title.lower()}, and I'm recording it so we "
                    f"have the notes. Let's give people a minute to join.")]
    for p in people:
        if p != host and rnd.random() < 0.6:
            lines.append((p, rnd.choice([f"Hey {h}, I'm here.", "Morning everyone.", "Hi all, sorry, I was on another call.",
                                         "Hello! Can you hear me okay?", "Hi, joining from my phone for the first few minutes."])))
    lines.append((host, "Great, I think we have everyone. Let me share the agenda."))
    return lines


def _close_lines(rnd, host, people):
    out = [(host, "Okay, let me recap the action items before we drop.")]
    for p in rnd.sample([x for x in people if x != host], min(3, len(people) - 1)):
        out.append((p, rnd.choice(["I'll send that out by end of day tomorrow.", "Got it, I'll own that one.",
                                   "I'll follow up in the channel once I have the numbers.",
                                   "I'll put a draft in the shared folder and tag everyone."])))
    out.append((host, "Perfect. Thanks everyone, see you next week."))
    return out


def _leadership(rnd, ppl):
    arr = rnd.randint(1800, 2600) / 100
    return [
        (0, f"First, the headline numbers. We closed the month at {arr:.1f} million in annual recurring revenue, which "
            f"is up {rnd.randint(3, 7)} percent month over month."),
        (1, f"Net revenue retention is holding at {rnd.randint(108, 124)} percent. Gross margin came in at "
            f"{rnd.randint(72, 81)} percent, a little better than plan because hosting costs were flat."),
        (3, f"On sales, we signed {rnd.randint(6, 14)} new logos. Two of the larger deals slipped into next month, "
            "both are in legal review and I expect them to close in the first two weeks."),
        (0, "What's the risk on those two? Is it pricing or is it the security questionnaire again?"),
        (3, "One is pricing, they want a multi year discount. The other is the security review, which Tomas is helping with."),
        (2, f"Engineering shipped the new export pipeline. Uptime was {rnd.choice(['99.95', '99.97', '99.92'])} percent. "
            "We had one incident on the ingestion service that we'll cover in the postmortem on Thursday."),
        (6, f"Marketing generated {rnd.randint(380, 900)} qualified leads, about ten percent above target. "
            "The webinar series is performing best, the paid social campaign less so, so I'm shifting budget."),
        (0, "Good. Let's make sure the shift is reflected in the forecast Mateo is putting together."),
        (1, "Will do. I'd also like each of you to send me headcount changes for next quarter by Friday."),
        (2, "I have two open roles I want to keep, and one I'd like to convert to a contractor position."),
        (0, "That's fine, put the reasoning in the planning doc. Anything else before we wrap?"),
        (6, "Just a reminder that the customer advisory board is in three weeks, and I need speakers."),
    ]


def _finance(rnd, ppl):
    rev = rnd.randint(55, 75) / 10
    return [
        (1, f"Revenue for the quarter was {rev:.1f} million, which is {rnd.randint(2, 6)} percent ahead of budget."),
        (7, f"Operating expenses were {rnd.randint(61, 78) / 10:.1f} million. The biggest variance is cloud hosting, "
            f"which ran about {rnd.randint(80, 240)} thousand over because of the new data retention feature."),
        (0, "Is that a one time step up or does it scale with usage?"),
        (7, "It scales with usage, so we've modelled it as cost per terabyte stored. Engineering thinks they can cut it "
            "by a third with tiered storage."),
        (1, f"Cash at the end of the quarter was {rnd.randint(18, 42)} million. Burn was "
            f"{rnd.randint(4, 12) / 10:.1f} million a month, so runway is comfortably over two years."),
        (3, "Can we talk about collections? A few of my accounts are over sixty days."),
        (7, f"Yes, days sales outstanding went up to {rnd.randint(41, 58)} days. Three customers make up most of it. "
            "I'll send reminders this week and escalate the largest one to you."),
        (1, "Deferred revenue grew nicely, which is good, most of the annual renewals were paid up front."),
        (0, "Let's get the board pack draft by the twentieth, with the variance commentary written in plain language."),
        (7, "I'll have the draft ready. I'll include the bridge from budget to actuals and the updated forecast."),
    ]


def _sprint(rnd, ppl):
    pts = rnd.randint(34, 52)
    return [
        (4, f"Our velocity over the last three sprints averages {pts} points. I've put {pts + rnd.randint(-4, 3)} points "
            "into the proposed scope, so we have a little buffer."),
        (4, "The top priority is the usage dashboard. Customers keep asking for it on calls."),
        (5, "I estimated the backend for the dashboard at eight points. The aggregation queries are the tricky part."),
        (11, "Designs are final for the main view. The drill-down screens still need one review."),
        (9, "Before we commit, I want two points reserved for the alert tuning from the last incident."),
        (2, "Agreed, reliability work comes first. Hana, can we push the CSV export polish to next sprint?"),
        (4, "Yes, that works. Let me move it. So the sprint goal is ship the dashboard behind a feature flag."),
        (5, "One dependency, we need the new read replica before we can load test."),
        (9, "I'll have the replica up by Wednesday."),
        (11, "I'll do the drill-down review with Hana tomorrow morning."),
        (4, "Great, I'll finalise the board after this call. Any blockers people already know about?"),
        (5, "Just vacation, I'm out next Friday."),
    ]


def _postmortem(rnd, ppl):
    mins = rnd.randint(25, 70)
    return [
        (9, f"On Tuesday at 2 14 PM UTC, API latency rose sharply. The p99 went from about 300 milliseconds to over "
            f"four seconds for {mins} minutes."),
        (9, "The trigger was a configuration change that reduced the connection pool size on the ingestion service."),
        (5, "The change was meant for staging only. Our deployment tooling applied it to production because both "
            "environments shared the same parameter group."),
        (2, "How did we detect it?"),
        (9, "The latency alert fired after eight minutes. That's too slow, the threshold was set for a five minute window."),
        (8, f"From the customer side, we had {rnd.randint(4, 15)} support tickets, mostly about slow dashboards. "
            "Two enterprise customers asked for a written incident report."),
        (5, "We rolled back the parameter change and latency recovered within three minutes."),
        (9, "Action items. One, separate the parameter groups. Two, tighten the latency alert to a two minute window. "
            "Three, add a production change check to the deployment pipeline."),
        (2, "Let's also add this to the runbook. And Leilani, please send the customer report once we review the draft."),
        (8, "Will do, I'll keep it factual and include the timeline."),
    ]


def _pipeline(rnd, ppl):
    return [
        (3, f"Total pipeline for the quarter is {rnd.randint(4, 9)}.{rnd.randint(1, 9)} million, with "
            f"{rnd.randint(1, 3)}.{rnd.randint(1, 9)} million in commit."),
        (3, "Let's go through the top deals. Stonebridge Energy is in final negotiation. They want a pilot first."),
        (0, "I'm okay with a paid pilot. A free pilot sets the wrong expectation."),
        (8, "From the customer success side, a paid pilot also gets us a real project sponsor."),
        (3, "Agreed. Next, Copperline Media. Champion left the company last week, so that deal is at risk."),
        (6, "We met two other people from Copperline at the conference. I can share their details."),
        (3, "That would help. Third, Juniper Learning, they are comparing us to a cheaper competitor."),
        (0, "Let's lead with the time to value story, not price. We have the case study from Bluefield."),
        (3, f"Win rate this quarter is {rnd.randint(22, 34)} percent. Average sales cycle is {rnd.randint(48, 85)} days."),
        (0, "Fine. Elliot, update the forecast categories by Thursday so finance can use them."),
    ]


def _close(rnd, ppl):
    return [
        (7, "We're on day three of close. Bank reconciliations are done for both operating accounts."),
        (1, "Good. Where are we with the card transactions?"),
        (7, f"About {rnd.randint(85, 97)} percent of card expenses have receipts. I've sent reminders to the rest. "
            "Most of the missing ones are small meals and rideshare."),
        (1, "Let's accrue for the hosting invoice that hasn't arrived yet."),
        (7, f"Already done, I accrued {rnd.randint(140, 260)} thousand based on the usage report."),
        (1, "And the prepaid software, did we update the amortisation schedule for the new annual contracts?"),
        (7, "Yes, three new contracts added. Revenue recognition schedules are also updated for the multi year deals."),
        (1, "Great. Payroll accrual and the bonus accrual?"),
        (7, "Payroll is booked. Bonus accrual is at one twelfth of the annual target, same as last month."),
        (1, "Okay. Target is to lock the books on day six and send the flash report to Dana on day seven."),
    ]


def _design(rnd, ppl):
    return [
        (11, "I'll share my screen. This is the new usage dashboard. The top row shows four summary cards."),
        (4, "I like the cards. Can we make the date range picker more obvious? Customers miss it today."),
        (11, "Sure, I can move it to the top right next to the export button."),
        (5, "For the chart, how many data points are we planning to show? Daily data over a year is a lot of points."),
        (11, "We aggregate to weekly beyond ninety days. The tooltip shows the exact values."),
        (8, "Customers always ask how usage compares to their contract. Can we show the contracted amount as a line?"),
        (4, "That's a great idea. It also helps with expansion conversations."),
        (11, "I'll add a dashed line for the contracted limit, with a label."),
        (5, "Accessibility check, the green and red colours need a second cue besides colour."),
        (11, "Good point, I'll add icons and make sure contrast passes."),
        (4, "Let's do one more review on Friday, then hand off to engineering."),
    ]


def _onboarding(rnd, ppl):
    return [
        (8, "Welcome! Today we'll walk through the setup plan and agree on the timeline for your go live."),
        (8, "Fernhill's team couldn't make the call live, so I'll record it and send the summary. "
            "Hana and Kofi are here to cover product and technical setup."),
        (5, "On the technical side, the first step is connecting your data warehouse. We support read only credentials."),
        (4, "Then we configure the three dashboards you picked during the pilot: shipments, delays, and cost per route."),
        (8, f"The target go live is in {rnd.randint(3, 6)} weeks. Training sessions for the operations team are in week two."),
        (5, "We'll also set up single sign on. I'll need your identity provider metadata."),
        (8, "I'll send a checklist after the call, with owners and dates for each item."),
        (4, "And we'll schedule a check-in thirty days after launch to review adoption."),
    ]


def _marketing(rnd, ppl):
    return [
        (6, f"Next quarter's campaign budget is {rnd.randint(180, 420)} thousand. I propose forty percent events, "
            "thirty percent paid, twenty percent content, and ten percent experiments."),
        (3, "Events work best for us. The last conference produced most of our enterprise pipeline."),
        (0, "What about the analyst briefing? That's been on the list for a while."),
        (6, "It's in the plan for the second month. We need two customer references for it."),
        (4, "We're launching the usage dashboard that quarter too. Can the campaign anchor on that?"),
        (6, "Yes, the launch can be the main story. Webinar, blog post, and a short demo video."),
        (3, "Please make sure the sales team gets a one pager and the demo script a week before launch."),
        (6, f"Our target is {rnd.randint(900, 1600)} marketing qualified leads and a cost per lead under "
            f"{rnd.randint(90, 160)} dollars."),
        (0, "Sounds good, let's review the results monthly instead of at the end of the quarter."),
    ]


def _eng_allhands(rnd, ppl):
    return [
        (2, "Welcome to the engineering all-hands. Three topics today: what we shipped, reliability, and hiring."),
        (2, f"We shipped {rnd.randint(30, 60)} pull requests to production this month, including the export pipeline."),
        (9, f"Reliability, uptime was {rnd.choice(['99.95', '99.96', '99.9'])} percent. Mean time to recovery was "
            f"{rnd.randint(12, 40)} minutes, down from last month."),
        (5, "I want to highlight the migration to the new queue system. It cut processing costs noticeably."),
        (11, "On design, the component library now covers ninety percent of the product screens."),
        (2, "On hiring, we have two offers out, a backend engineer and a data engineer."),
        (4, "From product, the roadmap for next quarter is on the wiki. Please add comments by Friday."),
        (2, "Open questions? Feel free to unmute or drop them in the chat."),
        (5, "Will we keep the on-call rotation at one week?"),
        (9, "Yes, one week, but we're adding a secondary on-call to reduce the load."),
    ]


def _budget(rnd, ppl):
    return [
        (1, f"For fiscal 2027, the plan assumes revenue growth of {rnd.randint(35, 60)} percent and a gross margin of "
            f"{rnd.randint(74, 80)} percent."),
        (1, "Operating expenses grow more slowly than revenue, so we reach break even in the fourth quarter."),
        (2, f"Engineering asks for {rnd.randint(6, 12)} new roles. Most are backend and data engineering."),
        (3, f"Sales wants {rnd.randint(4, 8)} account executives and two sales engineers."),
        (6, "Marketing would like a flat program budget but one additional content marketer."),
        (0, "That's more headcount than the plan supports. Let's phase the hiring, half in the first half, half later."),
        (7, "I'll model the phased version. Hiring later in the year cuts expense by about a quarter."),
        (1, "We also need to plan for the price increase on renewals, which adds roughly three percent to revenue."),
        (0, "Okay. Mateo, can you have version two ready by next Wednesday?"),
        (1, "Yes, with the phased hiring and three scenarios: base, upside, and downside."),
    ]


def _hiring(rnd, ppl):
    return [
        (10, "Thanks for joining the debrief. Let's go round the room. Please share your score and the key evidence."),
        (5, "I'd say strong yes. The system design was clear, they discussed trade offs between consistency and latency well."),
        (9, "Yes from me. Good debugging approach and they asked smart questions about our on-call process."),
        (2, "Lean yes. Technically strong. I'd like to see more evidence of mentoring, since this is a senior role."),
        (10, "The references both mentioned mentoring junior engineers, so that may address your concern."),
        (2, "In that case I'm comfortable with a yes."),
        (10, f"Great. The salary expectation is within the band. I'll prepare an offer at level five."),
        (10, "I'll send the offer by Thursday. Kofi, could you have a call with them to talk about the team?"),
        (5, "Happy to."),
    ]


def _retro(rnd, ppl):
    return [
        (4, "Let's start with what went well."),
        (5, "We shipped the dashboard behind the flag on time, and the load test passed on the first try."),
        (11, "Design and engineering collaboration was much smoother. The early review really helped."),
        (4, "What didn't go well?"),
        (9, "The read replica took longer than planned because of a permissions issue."),
        (2, "We also had too much work in progress in the middle of the sprint."),
        (5, "Code reviews took a while. Some pull requests waited more than a day."),
        (4, "Ideas for next sprint?"),
        (2, "Let's set a work in progress limit of two per person."),
        (5, "And a rule that pull requests get a first review within four hours."),
        (4, "I'll add both to our working agreement. Let's check them at the next retro."),
    ]


def _qbr(rnd, ppl):
    return [
        (8, "Thanks for meeting with us for the quarterly business review of the Tidewater Health account."),
        (8, f"Active users grew from {rnd.randint(120, 180)} to {rnd.randint(190, 260)} this quarter, and weekly "
            "usage is now steady across all three regions."),
        (4, "The features used most are scheduled reports and the capacity planning view."),
        (3, "Your contract renews in four months. We'd like to discuss adding the forecasting module."),
        (0, "We're also very interested in your feedback on the roadmap."),
        (8, "Tidewater's team asked for better role permissions, which is on the roadmap for next quarter."),
        (4, "I'll share the beta timeline so they can join early."),
        (8, "We'll follow up with the usage report and the renewal proposal by the end of the month."),
    ]


def _security(rnd, ppl):
    return [
        (9, "Quarterly security and compliance update. First, the SOC 2 audit window is open and evidence collection "
            f"is {rnd.randint(60, 85)} percent complete."),
        (9, "Access reviews for production systems are done. We removed seven accounts that were no longer needed."),
        (2, "Laptop encryption compliance is at a hundred percent, and endpoint protection is installed everywhere."),
        (10, "Security awareness training completion is at ninety four percent. The remaining people are on leave."),
        (1, "On vendors, we finished the risk reviews for our three critical vendors."),
        (9, "Penetration test is scheduled for next month. Findings from the last test are all closed."),
        (2, "We should also run a tabletop exercise for a data breach scenario."),
        (9, "Agreed, I'll schedule one for the leadership team in the next six weeks."),
    ]


def _voice(cache, name):
    path = os.path.join(cache, name + ".onnx")
    if not os.path.exists(path):
        s = session()
        for suffix in (".onnx", ".onnx.json"):
            r = s.get(f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{VOICE_PATH[name]}/{name}{suffix}",
                      timeout=300)
            r.raise_for_status()
            with open(path.replace(".onnx", suffix), "wb") as f:
                f.write(r.content)
    return path


def _tile_frames(tmp, title, people, size=(1280, 720)):
    """One gallery-view frame per active speaker (green border on the speaker), Zoom-style."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 22)
        big = ImageFont.truetype("DejaVuSans-Bold.ttf", 64)
        small = ImageFont.truetype("DejaVuSans.ttf", 16)
    except OSError:
        font = big = small = ImageFont.load_default()
    n = len(people)
    cols = 2 if n <= 4 else 3
    rows = (n + cols - 1) // cols
    W, H = size
    top = 40
    tw, th = (W - 20) // cols - 10, (H - top - 20) // rows - 10
    colours = ["#3b6ea5", "#7a4fa3", "#2f8f6b", "#b5643c", "#a33b5c", "#4f6d7a", "#8a7a2e"]
    frames = {}
    for active in [None] + people:
        img = Image.new("RGB", size, "#1a1a1a")
        d = ImageDraw.Draw(img)
        d.text((14, 10), title, fill="#dddddd", font=small)
        for k, p in enumerate(people):
            r, c = divmod(k, cols)
            x, y = 15 + c * (tw + 10), top + r * (th + 10)
            d.rectangle([x, y, x + tw, y + th], fill="#2b2b2b")
            initials = "".join(w[0] for w in PEOPLE[p][0].split()[:2])
            cx, cy, rad = x + tw // 2, y + th // 2 - 10, min(tw, th) // 4
            d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=colours[p % len(colours)])
            d.text((cx, cy), initials, fill="white", font=big, anchor="mm")
            d.rectangle([x + 6, y + th - 34, x + 6 + 12 * len(PEOPLE[p][0]) + 16, y + th - 6], fill="#000000")
            d.text((x + 14, y + th - 31), PEOPLE[p][0], fill="white", font=font)
            if p == active:
                d.rectangle([x, y, x + tw, y + th], outline="#2ecc40", width=5)
        path = os.path.join(tmp, f"frame_{active}.png")
        img.save(path)
        frames[active] = path
    return frames


def _render(script, people, title, start, voices_dir, tmp):
    from piper import PiperVoice
    loaded = {}
    clips, cues, t = [], [], 0.0
    rate = None
    for k, (who, text) in enumerate(script):
        vname = PEOPLE[who][2]
        if vname not in loaded:
            loaded[vname] = PiperVoice.load(_voice(voices_dir, vname))
        wav = os.path.join(tmp, f"u{k:04d}.wav")
        with wave.open(wav, "wb") as w:
            loaded[vname].synthesize_wav(text, w)
        with wave.open(wav) as w:
            dur = w.getnframes() / w.getframerate()
            rate = rate or w.getframerate()
        gap = random.Random(k).uniform(0.35, 1.1)
        clips.append((wav, who, dur, gap))
        cues.append((t, t + dur, who, text))
        t += dur + gap
    frames = _tile_frames(tmp, f"{COMPANY} - {title}", people)
    # audio: utterances separated by silence, resampled to one rate
    lst = os.path.join(tmp, "audio.txt")
    with open(lst, "w") as f:
        for k, (wav, _, _, gap) in enumerate(clips):
            sil = os.path.join(tmp, f"s{k:04d}.wav")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                            f"anullsrc=r=22050:cl=mono", "-t", f"{gap:.3f}", sil], check=True)
            norm = wav.replace(".wav", "n.wav")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ar", "22050", "-ac", "1", norm], check=True)
            f.write(f"file '{norm}'\nfile '{sil}'\n")
    audio = os.path.join(tmp, "audio.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", audio],
                   check=True)
    vl = os.path.join(tmp, "video.txt")
    with open(vl, "w") as f:
        for wav, who, dur, gap in clips:
            f.write(f"file '{frames[who]}'\nduration {dur:.3f}\nfile '{frames[None]}'\nduration {gap:.3f}\n")
        f.write(f"file '{frames[None]}'\n")
    mp4 = os.path.join(tmp, "out.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", vl, "-i", audio,
                    "-vf", "fps=10,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
                    "-c:a", "aac", "-b:a", "64k", "-shortest", mp4], check=True)
    m4a = os.path.join(tmp, "out.m4a")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio, "-c:a", "aac", "-b:a", "64k", m4a], check=True)
    vtt = ["WEBVTT", ""]
    for k, (a, b, who, text) in enumerate(cues, 1):
        vtt += [str(k), f"{_vtt_time(a)} --> {_vtt_time(b)}", f"{PEOPLE[who][0]}: {text}", ""]
    return mp4, m4a, "\n".join(vtt), t


def _chat(rnd, people, start, total):
    msgs = ["Agenda doc is in the calendar invite.", "Can everyone see my screen?", "+1",
            "I'll take that action item.", "Link to the dashboard is in the channel.", "Sorry, my connection dropped for a second.",
            "Thanks, very helpful.", "Can we get the slides after the call?", "Agreed.", "Notes are in the shared folder."]
    out = []
    for _ in range(rnd.randint(4, 10)):
        t = start + timedelta(seconds=rnd.uniform(30, max(60, total - 30)))
        out.append((t, rnd.choice(people), rnd.choice(msgs)))
    return "\n".join(f"{t:%H:%M:%S} From {PEOPLE[p][0]} to Everyone:\n\t{m}" for t, p, m in sorted(out)) + "\n"


def generated(sink, st):
    done = st.setdefault("zoom_made", 0)
    voices = os.path.abspath("cache/voices")
    os.makedirs(voices, exist_ok=True)
    meetings = _meetings()[:MADE]
    n = 0
    base_day = datetime(2026, 9, 1, 14, 0, 0)
    while done < len(meetings) and not sink.full():
        title, host, people, builder = meetings[done]
        rnd = random.Random(done)
        start = base_day + timedelta(days=done * 2 + done // 5 * 2, hours=rnd.randint(-4, 3))
        script = _open(rnd, host, people, title) + builder(rnd, people) + _close_lines(rnd, host, people)
        tmp = tempfile.mkdtemp()
        try:
            mp4, m4a, vtt, total = _render(script, people, title, start, voices, tmp)
            stamp = f"GMT{start:%Y%m%d-%H%M%S}"
            folder = f"{ZOOM}/Generated Calls/{start:%Y-%m-%d} {title}"
            for src, name in ((mp4, f"{stamp}_Recording_gallery_1280x720.mp4"), (m4a, f"{stamp}_Recording.m4a")):
                p = sink.path(f"{folder}/{name}")
                shutil.move(src, p)
                sink.wrote(p)
            sink.write_text(f"{folder}/{stamp}_Recording.transcript.vtt", vtt)
            sink.write_text(f"{folder}/{stamp}_RecordingnewChat.txt", _chat(rnd, people, start, total))
            out = io.StringIO()
            w = csv.writer(out)
            w.writerow(["Name (Original Name)", "User Email", "Join Time", "Leave Time", "Duration (Minutes)", "Guest"])
            for p in people:
                j = start + timedelta(seconds=rnd.randint(0, 90))
                lv = start + timedelta(seconds=total + rnd.randint(5, 40))
                w.writerow([PEOPLE[p][0], f"{PEOPLE[p][0].lower().replace(' ', '.')}@{DOMAIN}",
                            f"{j:%m/%d/%Y %I:%M:%S %p}", f"{lv:%m/%d/%Y %I:%M:%S %p}",
                            max(1, round((lv - j).seconds / 60)), "No"])
            sink.write_text(f"{folder}/participants_{stamp}.csv", out.getvalue())
            sink.write_text(f"{folder}/meeting_details.json", json.dumps({
                "topic": title, "host": PEOPLE[host][0], "start_time": start.isoformat() + "Z",
                "duration_minutes": round(total / 60), "participants": len(people),
                "meeting_id": f"{rnd.randint(800, 999)} {rnd.randint(1000, 9999)} {rnd.randint(1000, 9999)}"}, indent=1))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        done += 1
        st["zoom_made"] = done
        n += 1
    return n


SOURCES = {"zoom_real": real, "zoom_generated": generated}
