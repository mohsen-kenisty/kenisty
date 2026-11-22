#!/usr/bin/env python3
"""يحوّل ملفات USFM (مجلد أو ملف مضغوط zip) إلى bible.json لبرنامج كنيستي القبطية.
الاستخدام:  python3 usfm2json.py  مسار_المجلد_أو_zip  bible.json
"""
import re, sys, os, json, glob, zipfile

ORDER = ("GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN "
         "HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI "
         "TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV").split()
NAMES = dict(zip(ORDER, ("التكوين الخروج اللاويين العدد التثنية يشوع القضاة راعوث صموئيل_الأول صموئيل_الثاني ملوك_الأول ملوك_الثاني "
  "أخبار_الأيام_الأول أخبار_الأيام_الثاني عزرا نحميا أستير أيوب المزامير الأمثال الجامعة نشيد_الأنشاد إشعياء إرميا مراثي_إرميا حزقيال دانيال "
  "هوشع يوئيل عاموس عوبديا يونان ميخا ناحوم حبقوق صفنيا حجي زكريا ملاخي متى مرقس لوقا يوحنا أعمال_الرسل رومية كورنثوس_الأولى كورنثوس_الثانية "
  "غلاطية أفسس فيلبي كولوسي تسالونيكي_الأولى تسالونيكي_الثانية تيموثاوس_الأولى تيموثاوس_الثانية تيطس فليمون العبرانيين يعقوب بطرس_الأولى "
  "بطرس_الثانية يوحنا_الأولى يوحنا_الثانية يوحنا_الثالثة يهوذا رؤيا_يوحنا").split()))
NAMES = {k: v.replace('_', ' ') for k, v in NAMES.items()}

CHAR_OPEN = r'\\\+?(?:w|wj|add|nd|qt|tl|pn|k|sc|bd|it|em|bk|ord|sig|sls|ndx|png|wg|wh|wa|rb|jmp|ior|qac|qs|vp|bdit|no|sup)\s'
def clean(t):
    t = re.sub(r'\\f\s.*?\\f\*', '', t, flags=re.S)           # حواشي
    t = re.sub(r'\\x\s.*?\\x\*', '', t, flags=re.S)           # مراجع
    t = re.sub(r'\|[^\\]*?(?=\\\+?[a-z]+\*)', '', t)           # سمات \w كلمة|lemma="..."\w*
    t = re.sub(r'\\\+?[a-z]+\d?\*', '', t)                     # علامات الإغلاق
    t = re.sub(CHAR_OPEN, '', t)
    t = re.sub(r'\\[a-z]+\d*\s?', '', t)                      # أي علامة متبقية
    return re.sub(r'\s+', ' ', t).strip()

SKIP = re.compile(r'^(ide|sts|rem|h|toc\d|mt\d?|mte\d?|imt\d?|ip|is\d?|ms\d?|mr|s\d?|sr|r|d|sp|cl|cd|cp|ca|va|vp|periph|restore)$')
def parse(txt):
    b = {'id': '', 'n': '', 'c': []}; ch = None; cur = None; name = {}
    for raw in txt.splitlines():
        line = raw.strip()
        if not line.startswith('\\'):
            if cur is not None and line: ch[cur] += ' ' + line
            continue
        m = re.match(r'\\(\+?[a-z]+\d?)\*?\s*(.*)', line)
        if not m: continue
        mk, rest = m.group(1), m.group(2)
        if mk == 'id': b['id'] = rest.split()[0].upper() if rest.split() else ''
        elif mk in ('h', 'toc1', 'toc2', 'toc3'): name.setdefault(mk, clean(rest))
        elif mk == 'c':
            n = int(re.match(r'\d+', rest).group()); 
            while len(b['c']) < n: b['c'].append([])
            ch = b['c'][n - 1]; cur = None
        elif mk == 'v' and ch is not None:
            vm = re.match(r'(\d+)\S*\s*(.*)', rest)
            if not vm: continue
            cur = int(vm.group(1)) - 1
            while len(ch) <= cur: ch.append('')
            ch[cur] = (ch[cur] + ' ' + vm.group(2)).strip()
        elif SKIP.match(mk): continue
        elif cur is not None and rest: ch[cur] += ' ' + rest   # فقرات وأبيات شعر
    b['c'] = [[clean(v) for v in c] for c in b['c']]
    b['n'] = name.get('toc2') or name.get('h') or name.get('toc3') or name.get('toc1') or NAMES.get(b['id'], b['id'])
    return b

def main(src, out):
    files = []
    if src.lower().endswith('.zip'):
        z = zipfile.ZipFile(src); texts = [z.read(n).decode('utf-8-sig') for n in z.namelist() if re.search(r'\.(usfm|sfm|usx?)$', n, re.I) and not n.endswith('/')]
    else:
        fl = [f for f in glob.glob(os.path.join(src, '**', '*'), recursive=True) if re.search(r'\.(usfm|sfm)$', f, re.I)]
        texts = [open(f, encoding='utf-8-sig').read() for f in sorted(fl)]
    books = [parse(t) for t in texts]
    books = [b for b in books if b['id'] and b['c']]
    pos = lambda b: ORDER.index(b['id']) if b['id'] in ORDER else 999
    books.sort(key=pos)
    json.dump({'v': 1, 'books': books}, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(len(books), 'سفر،', sum(len(b['c']) for b in books), 'أصحاح،', sum(1 for b in books for c in b['c'] for v in c if v), 'آية ->', out, os.path.getsize(out) // 1024, 'KB')

if __name__ == '__main__':
    if len(sys.argv) != 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
