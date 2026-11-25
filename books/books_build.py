#!/usr/bin/env python3
"""يبني ملف كتاب لمكتبة برنامج كنيستي من ملف نصي أو HTML (أو مجلد فيه ملفات)،
ويضيفه لـ index.json في نفس المجلد.

أمثلة:
  python3 books_build.py kelma.txt --id kelma-manfa3a --title "كلمة منفعة" --author "اسم المؤلف"
  python3 books_build.py مجلد_الملفات --id my-book --title "عنوان الكتاب"

العناوين اللي بيتعرف عليها: «1) ...» أو «5- ...» أو «# ...» أو «كلمة 5 ...» أو «الفصل ...».
لو ما لقاش عناوين بيقسّم النص أجزاء حوالي 1500 حرف.
اتأكد إن عندك حق استخدام النص قبل ما تنشره على مستودع عام.
"""
import argparse, glob, html, json, os, re, sys

def decode(raw):
    for enc in ("utf-8-sig", "cp1256"):
        try:
            t = raw.decode(enc)
            if "\ufffd" not in t: return t
        except Exception: pass
    return raw.decode("utf-8", "ignore")

def to_text(t):
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    if re.search(r"<(p|div|br|h\d|body)\b", t, re.I):
        t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
        t = re.sub(r"(?i)<br\s*/?>|</(p|div|h\d|li|tr|td)>", "\n", t)
        t = html.unescape(re.sub(r"<[^>]+>", "", t))
    return t

HEAD = re.compile(r"^(#{1,3}\s*\S|\d{1,3}\s*[-–.)]\s*\S)")
HEAD2 = re.compile(r"^(كلمة|الكلمة|الفصل|الباب|الأصحاح|مقال|المقال)\s+\S+")
def is_head(l): return bool(l) and len(l) <= 90 and (HEAD.match(l) or (HEAD2.match(l) and len(l) <= 60))

def split_text(t):
    lines = [re.sub(r"\s+", " ", x).strip() for x in to_text(t).split("\n")]
    blanks = sum(1 for x in lines if not x); sep = blanks / max(1, len(lines) - blanks) >= 0.3
    paras, buf = [], ""
    for l in lines:
        if not l:
            if buf: paras.append(buf); buf = ""
            continue
        if is_head(l):
            if buf: paras.append(buf); buf = ""
            paras.append({"h": re.sub(r"^\d{1,3}\s*[-–.)]\s*", "", re.sub(r"^#+\s*", "", l))}); continue
        if sep: buf = (buf + " " + l) if buf else l
        else: paras.append(l)
    if buf: paras.append(buf)
    heads = [p for p in paras if isinstance(p, dict)]
    secs = []
    if len(heads) >= 3:
        cur = None
        for p in paras:
            if isinstance(p, dict):
                if cur and cur["t"]: secs.append(cur)
                cur = {"h": p["h"], "t": ""}
            elif cur: cur["t"] += ("\n\n" if cur["t"] else "") + p
        if cur and cur["t"]: secs.append(cur)
    else:
        cur, n = "", 1
        for p in paras:
            s = p["h"] if isinstance(p, dict) else p
            if len(cur + s) > 1500 and cur:
                secs.append({"h": f"جزء {n}", "t": cur.strip()}); n += 1; cur = ""
            cur += ("\n\n" if cur else "") + s
        if cur.strip(): secs.append({"h": f"جزء {n}", "t": cur.strip()})
    return [s for s in secs if s["t"]]

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input"); ap.add_argument("--id", required=True); ap.add_argument("--title", required=True)
    ap.add_argument("--author", default=""); ap.add_argument("--src", default="")
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.input, "*"))) if os.path.isdir(a.input) else [a.input]
    text = "\n\n".join(decode(open(f, "rb").read()) for f in files if re.search(r"\.(txt|html?|md)$", f, re.I))
    secs = split_text(text)
    if not secs: sys.exit("ما لقيتش نص يتقسّم. اتأكد من الملف.")
    book = {"id": a.id, "title": a.title, "author": a.author, "src": a.src, "sections": secs}
    os.makedirs(a.out, exist_ok=True)
    json.dump(book, open(os.path.join(a.out, a.id + ".json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    ip = os.path.join(a.out, "index.json")
    idx = json.load(open(ip, encoding="utf-8")) if os.path.exists(ip) else {"books": []}
    idx["books"] = [b for b in idx["books"] if b["id"] != a.id] + [{"id": a.id, "title": a.title, "author": a.author, "file": a.id + ".json", "sections": len(secs)}]
    json.dump(idx, open(ip, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"تم: {len(secs)} قسم -> {a.id}.json (وتحدّث index.json)")

if __name__ == "__main__": main()
