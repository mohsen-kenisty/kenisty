#!/usr/bin/env python3
"""يحمّل كتاب من موقع الأنبا تكلا (صفحات HTML) ويبنيه ملف كتاب لمكتبة برنامج «كنيستي».
للاستخدام الشخصي: الكتب عليها حقوق، فاستورد الملف في البرنامج على جهازك، ولا تنشره على مستودع عام من غير إذن.

مثال (في Colab):
  !python -u books_fetch.py --url "رابط فهرس الكتاب" --id kelma-manfa3a --title "كلمة منفعة" --author "اسم المؤلف"
"""
import argparse, html, json, os, re, sys, time, urllib.parse, urllib.request

MARK = "نرجو الصلاة من أجل خدمة الموقع والخدام"
AR = re.compile(r"[\u0600-\u06FF]")

def decode(raw, header_cs):
    cands = [c for c in (header_cs,) if c]
    m = re.search(rb'charset=["\']?([\w-]+)', raw[:3000], re.I)
    if m: cands.append(m.group(1).decode("ascii", "ignore"))
    cands += ["utf-8", "cp1256"]
    for c in cands:
        try: return raw.decode(c)
        except Exception: pass
    return raw.decode("cp1256", "ignore")

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "kenisty-church-app/1.0 (personal church use)"})
    r = urllib.request.urlopen(req, timeout=30)
    return decode(r.read(), r.headers.get_content_charset())

def links(page, url):
    out = []
    for h in re.findall(r'href=["\']([^"\'#]+)', page):
        u = urllib.parse.urljoin(url, h).split("#")[0]
        if u.endswith(".html"): out.append(u)
    return out

def strip(t): return html.unescape(re.sub(r"<[^>]+>", " ", t))
def norm(s): return re.sub(r"\s+", " ", s).strip()

def page_title(page):
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", page)
    return norm(strip(m.group(1))).split(" < ")[0].strip() if m else ""

def page_lines(page, title):
    page = re.sub(r"(?is)<(script|style|nav|footer|select)[^>]*>.*?</\1>", " ", page)
    anchors = {norm(strip(a)) for a in re.findall(r"(?is)<a\b[^>]*>(.*?)</a>", page)}
    page = re.sub(r"(?i)<br\s*/?>|</(p|div|tr|li|h\d|td|ul|table)>", "\n", page)
    text = strip(page)
    if MARK in text: text = text.split(MARK)[-1]
    out = []
    for raw in text.split("\n"):
        s = norm(raw)
        if not s or "|" in s: continue
        if s.startswith("الكتاب المقدس (+"): break          # بداية فوتر الموقع
        if "تقصير الرابط" in s or "St-Takla" in s or s.startswith("http"): continue
        if not AR.search(s): continue
        if s in anchors and not re.match(r"^\d", s): continue  # روابط السابق/التالي/الفهرس
        out.append(s)
    # شيل السطور اللي هي عنوان الصفحة نفسه أو عنوان السلسلة في الأول
    while out and (out[0] in title or title in out[0] or out[0].startswith("كتاب ")) and len(out) > 1: out.pop(0)
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True, help="رابط فهرس الكتاب")
    ap.add_argument("--id", required=True); ap.add_argument("--title", required=True)
    ap.add_argument("--author", default=""); ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--max", type=int, default=400, help="أقصى عدد صفحات")
    ap.add_argument("--out", default=".")
    a = ap.parse_args()
    base = a.url.rsplit("/", 1)[0] + "/"
    seen, queue, secs = set(), [a.url], []
    while queue and len(seen) < a.max + 20:
        u = queue.pop(0)
        if u in seen: continue
        seen.add(u)
        try: p = get(u)
        except Exception as e: print("تعذر:", u, e); continue
        time.sleep(a.delay)
        name = u.rsplit("/", 1)[1].lower()
        if "index" in name:                                  # صفحة فهرس: نجمع روابطها
            queue += [l for l in links(p, u) if l.startswith(base) and l not in seen and l not in queue]
            print("فهرس:", name)
        else:
            t = page_title(p); ls = page_lines(p, t)
            if ls:
                secs.append({"h": t or f"قسم {len(secs)+1}", "t": "\n\n".join(ls)})
                print(len(secs), (t or name)[:60])
    if not secs: sys.exit("ما لقيتش صفحات نصية. اتأكد من الرابط (لازم يكون فهرس الكتاب).")
    book = {"id": a.id, "title": a.title, "author": a.author, "src": "موقع الأنبا تكلا هيمانوت (st-takla.org)", "sections": secs}
    os.makedirs(a.out, exist_ok=True)
    json.dump(book, open(os.path.join(a.out, a.id + ".json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    ip = os.path.join(a.out, "index.json")
    idx = json.load(open(ip, encoding="utf-8")) if os.path.exists(ip) else {"books": []}
    idx["books"] = [b for b in idx["books"] if b["id"] != a.id] + [{"id": a.id, "title": a.title, "author": a.author, "file": a.id + ".json", "sections": len(secs)}]
    json.dump(idx, open(ip, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"تم: {len(secs)} قسم -> {a.id}.json")

if __name__ == "__main__": main()
