# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
import json, re, collections
from pathlib import Path
har_path = Path(r"<descargas>\w1.har")
out_dir = har_path.parent
data = json.loads(har_path.read_text(encoding="utf-8", errors="replace"))
entries = data.get("log", {}).get("entries", [])
print("ENTRIES", len(entries))
ws_entries = []
frames = []
for e in entries:
    req = e.get("request", {})
    url = req.get("url", "")
    # Chrome HAR may put WS frames in _webSocketMessages
    msgs = e.get("_webSocketMessages") or e.get("webSocketMessages")
    if msgs or "10086" in url or url.startswith("ws://"):
        ws_entries.append({"url": url, "n": len(msgs or []), "status": e.get("response", {}).get("status")})
        for m in (msgs or []):
            # typ: send/receive, data, time, opcode
            typ = m.get("type") or m.get("opcode")
            direction = "tx" if m.get("type") == "send" else ("rx" if m.get("type") == "receive" else str(m.get("type")))
            payload = m.get("data")
            frames.append({
                "dir": direction,
                "t": m.get("time"),
                "opcode": m.get("opcode"),
                "d": payload,
            })

print("WS_URLS")
for w in ws_entries:
    print(w)

print("FRAMES", len(frames))
tx = [f for f in frames if f["dir"] == "tx"]
rx = [f for f in frames if f["dir"] == "rx"]
print("TX", len(tx), "RX", len(rx))

# dump jsonl
jl = out_dir / "w1-from-har.jsonl"
with jl.open("w", encoding="utf8") as f:
    for fr in frames:
        f.write(json.dumps(fr, ensure_ascii=False) + "\n")
print("JSONL", jl)

# summarize hex-looking payloads
hex_re = re.compile(r"^[0-9a-fA-F]+$")
def brief(s):
    if s is None: return None
    s = str(s)
    if len(s) > 120: return s[:120] + "..."
    return s

print("\nFIRST_20")
for i, fr in enumerate(frames[:20]):
    print(i, fr["dir"], brief(fr["d"]))

# look for presence / connectionMethod patterns: starts with 81/83/84 etc
print("\nPREFIX_STATS_TX")
ctr = collections.Counter()
for fr in tx:
    d = str(fr.get("d") or "")
    if hex_re.match(d) and len(d) >= 4:
        ctr[d[:4].lower()] += 1
    elif hex_re.match(d.replace(" ", "")):
        ctr["spaced"] += 1
    else:
        ctr["nonhex"] += 1
print(ctr.most_common(20))

print("\nPREFIX_STATS_RX")
ctr = collections.Counter()
for fr in rx:
    d = str(fr.get("d") or "")
    if hex_re.match(d) and len(d) >= 4:
        ctr[d[:4].lower()] += 1
    else:
        ctr["other"] += 1
print(ctr.most_common(20))

# find write-like vs read-like (f0 = read from page typically)
print("\nSAMPLES_CONTAINING_f0")
n = 0
for fr in frames:
    d = str(fr.get("d") or "").lower().replace(" ", "")
    if "f0" in d[:10] or d.startswith("f0"):
        print(fr["dir"], brief(d))
        n += 1
        if n >= 15: break

print("\nSAMPLES_8301_or_presence")
n = 0
for fr in frames:
    d = str(fr.get("d") or "").lower().replace(" ", "")
    if d.startswith("8301") or d.startswith("8101") or d.startswith("8001") or d.startswith("8401"):
        print(fr["dir"], brief(d))
        n += 1
        if n >= 20: break

# report rate related: cmd 6 often
print("\nLIKELY_REPORT_RATE")
n = 0
for fr in frames:
    d = str(fr.get("d") or "").lower().replace(" ", "")
    if "0806" in d or d[4:8]=="0806" if len(d)>8 else False:
        print(fr["dir"], brief(d))
        n += 1
        if n >= 20: break

# if no _webSocketMessages, dump keys of first entry
if not frames and entries:
    e0 = entries[0]
    print("ENTRY0_KEYS", list(e0.keys()))
    print("REQ_URL", e0.get("request",{}).get("url"))
    # search nested for websocket
    raw = json.dumps(data)
    print("HAS__webSocketMessages", "_webSocketMessages" in raw)
    print("COUNT_token", raw.count("_webSocketMessages"))
    print("COUNT_ws_url", raw.count("10086"))
