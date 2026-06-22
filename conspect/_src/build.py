# coding: utf-8
"""Собирает ОБА прототипа конспекта из ПОЛНОГО файла personality 15.md:
  • PDF (conspect.html → PDF под iPhone): карточки-узлы с внутренними гиперссылками.
  • App (app/index.html): тот же дерево-JSON впечатывается в TMA-аутлайнер.
Один парсер → одно дерево → оба прототипа не расходятся. Текст узлов ДОСЛОВНЫЙ.

Модель PDF: карточка = узел + прямые дети. Узел-с-детьми — ссылка на свою карточку.
Путь наверх — хлебные крошки. Стрелки → разделитель «--- --- ↓↓↓ --- ---». Разделители → тонкая линия."""
import html, re, json

SRC = "/Users/creationstation/Library/Mobile Documents/iCloud~md~obsidian/Documents/light/personality 15.md"
APP_TEMPLATE = "/tmp/conspect-app/template.html"
APP_OUT = "/tmp/conspect-app/index.html"

# ── Парсер outline → лес узлов под виртуальным корнем ──
# Узлы: {"text":..,"children":[]} | {"divider":True} | {"arrow":True} | {"img":..,"caption":..}
def classify(content):
    """Тип контента после снятия маркера списка."""
    core = content.strip().strip("`").strip()
    if core == "":
        return "empty"
    if set(core) <= set("-↓↑ "):
        return "arrow" if ("↓" in core or "↑" in core) else "divider"
    return "text"

def parse_outline(path):
    with open(path, encoding="utf-8") as f:
        raw_lines = f.read().split("\n")
    root = {"text": "personality 15", "children": []}
    stack = [(-1, root)]            # (indent, node) — родители; терминалы не пушим
    for raw in raw_lines:
        line = raw.rstrip()
        if line.strip() == "":
            continue
        indent = len(line) - len(line.lstrip(" \t"))
        body = line.lstrip(" \t")
        heading = False
        # H2-секция → верхний уровень
        if body.startswith("## "):
            content = body[3:].strip()
            heading = True
            indent = 0
        else:
            m = re.match(r"^(\d+)\.\s+(.*)$", body, re.S)   # нумерованный
            if m:
                content = body                                # номер сохраняем в тексте (split_marker позже)
            elif body.startswith("- "):
                content = body[2:]
            elif body == "-":
                content = ""
            else:
                content = body                                # голый текст без маркера
        kind = classify(content)
        if kind == "empty":
            continue
        # выбрать родителя по отступу
        if heading:
            while stack[-1][0] >= 0:
                stack.pop()
        else:
            while stack[-1][0] >= indent:
                stack.pop()
        parent = stack[-1][1]
        if kind == "divider":
            parent["children"].append({"divider": True})
        elif kind == "arrow":
            parent["children"].append({"arrow": True})
        else:
            node = {"text": content, "children": []}
            if heading:
                node["heading"] = True
            parent["children"].append(node)
            stack.append((indent, node))
    return root

TREE = parse_outline(SRC)

# ── Тестовый узел-картинка (в конспекте картинок нет — внедряем искусственно, требование плана) ──
def insert_test_image(node):
    if node.get("text", "").startswith("1. dominance hierarchies"):
        img = {"img": "dominance_pyramid.jpg",
               "caption": "тестовый узел-картинка: схема dominance hierarchy (внедрена искусственно — в конспекте картинок нет)"}
        pos = min(2, len(node["children"]))
        node["children"].insert(pos, img)
        return True
    for ch in node.get("children", []):
        if insert_test_image(ch):
            return True
    return False
insert_test_image(TREE)

def is_node(ch):
    return "text" in ch and ch.get("children")

# ── Присвоить id (якоря карточек) и crumb (краткий ярлык) узлам-с-детьми ──
_counter = [0]
def clean_label(text):
    t = re.sub(r"[=*`]", "", text)
    t = re.sub(r"^\d+\.\s+", "", t).strip()
    return t[:24].rstrip() + ("…" if len(t) > 24 else "")
def assign_ids(node):
    if is_node(node):
        node["id"] = f"c{_counter[0]}"
        node["crumb"] = clean_label(node["text"])
        _counter[0] += 1
        for ch in node["children"]:
            assign_ids(ch)
TREE["id"] = "c-root"
TREE["crumb"] = "конспект"
for ch in TREE["children"]:
    assign_ids(ch)

# ── Карточки (обход в глубину): узел-с-детьми = карточка ──
cards = []  # (node, path) path = список (id, crumb) предков включая узел
def collect(node, path):
    path = path + [(node["id"], node["crumb"])]
    cards.append((node, path))
    for ch in node["children"]:
        if is_node(ch):
            collect(ch, path)
collect(TREE, [])

def markup(t):
    """HTML-escape + инлайн-разметка Obsidian: ==hl==, **bold**, `code`. Стрелки → ↑ ↓ остаются."""
    t = html.escape(t)
    t = re.sub(r"==(.+?)==", r"<mark>\1</mark>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t

def split_marker(text):
    """Маркер как в оригинале: ведущее 'N.' → номер, иначе буллет «—»."""
    m = re.match(r"^(\d+)\.\s+(.*)$", text, re.S)
    if m:
        return m.group(1) + ".", m.group(2)
    return "—", text

def render_breadcrumbs(path):
    parts = []
    for i, (cid, crumb) in enumerate(path):
        if i < len(path) - 1:
            parts.append(f'<a href="#{cid}">{html.escape(crumb)}</a>')
        else:
            parts.append(f'<span class="here">{html.escape(crumb)}</span>')
    return '<div class="crumbs">' + '<span class="sep">›</span>'.join(parts) + '</div>'

def render_children(children):
    out = []
    for ch in children:
        if ch.get("divider"):
            out.append('<div class="divider"></div>')
        elif ch.get("arrow"):
            out.append('<div class="arrow">↓↓↓</div>')
        elif ch.get("img"):
            out.append(
                f'<div class="leaf imgrow"><span class="bullet spacer">—</span>'
                f'<figure class="imgnode"><img src="{ch["img"]}" alt="test"><figcaption>{html.escape(ch["caption"])}</figcaption></figure></div>'
            )
        elif is_node(ch):
            mk, body = split_marker(ch["text"])
            out.append(
                f'<a class="dive" href="#{ch["id"]}">'
                f'<span class="bullet">{mk}</span>'
                f'<span class="dive-t">{markup(body)} <span class="dive-mark">▸</span></span>'
                f'</a>'
            )
        else:  # leaf
            mk, body = split_marker(ch["text"])
            out.append(f'<div class="leaf"><span class="bullet">{mk}</span><span class="leaf-t">{markup(body)}</span></div>')
    return "\n".join(out)

card_html = []
for idx, (node, path) in enumerate(cards):
    first = " first" if idx == 0 else ""
    title = node["text"] if node.get("id") == "c-root" else split_marker(node["text"])[1]
    card_html.append(f'''<section class="card{first}" id="{node["id"]}">
{render_breadcrumbs(path)}
<h2 class="node-title">{markup(title)}</h2>
<div class="kids">
{render_children(node["children"])}
</div>
</section>''')
CARDS = "\n".join(card_html)

HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>personality 15 — conspect prototype</title>
<style>
:root {{
  --accent:#6366f1; --accent-dark:#4338ca; --accent-light:#e0e7ff;
  --text:#1e293b; --text-dim:#64748b; --text-faint:#94a3b8;
  --bg:#ffffff; --card-bg:#f8fafc; --border:#e2e8f0; --mark:#fff3b0;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  background:var(--bg); color:var(--text);
  font-family:-apple-system,'Helvetica Neue','Arial',sans-serif;
  font-size:16px; line-height:1.6; -webkit-font-smoothing:antialiased;
}}
.cover {{
  display:flex; flex-direction:column; justify-content:center; height:100%;
  page-break-after:always; padding:8px 4px;
}}
.cover .kicker {{ font-size:13px; color:var(--accent); font-weight:700; letter-spacing:.08em; text-transform:uppercase; margin-bottom:14px; }}
.cover h1 {{ font-size:30px; font-weight:800; line-height:1.15; margin-bottom:18px; }}
.cover .rule {{ width:54px; height:3px; background:var(--accent); border-radius:2px; margin:14px 0 20px; }}
.cover .how {{ font-size:15px; color:var(--text-dim); line-height:1.55; }}
.cover .how b {{ color:var(--text); }}
.cover .meta {{ font-size:13px; color:var(--text-faint); margin-top:22px; }}

.card {{ page-break-before:always; page-break-inside:avoid; padding:6px 2px; }}
.card.first {{ page-break-before:auto; }}

.crumbs {{ font-size:13px; color:var(--text-faint); margin-bottom:14px; line-height:1.5; }}
.crumbs a {{ color:var(--accent); text-decoration:none; }}
.crumbs .sep {{ margin:0 6px; color:var(--border); }}
.crumbs .here {{ color:var(--text-dim); font-weight:600; }}

.node-title {{
  font-size:20px; font-weight:700; line-height:1.3; color:var(--text);
  margin-bottom:18px; page-break-after:avoid;
}}
.node-title mark {{ background:var(--mark); padding:0 2px; border-radius:2px; }}
.node-title code {{ font-family:ui-monospace,Menlo,monospace; font-size:.92em; background:var(--card-bg); padding:0 3px; border-radius:3px; }}

.kids {{ display:flex; flex-direction:column; gap:12px; }}

.leaf {{ display:flex; gap:9px; align-items:flex-start; page-break-inside:avoid; }}
.leaf .bullet {{ color:var(--text-faint); font-weight:700; flex-shrink:0; line-height:1.6; }}
.leaf-t {{ font-size:16px; line-height:1.6; }}
.leaf-t mark {{ background:var(--mark); padding:0 2px; border-radius:2px; }}
.leaf-t strong {{ font-weight:700; }}
.leaf-t code, .dive-t code {{ font-family:ui-monospace,Menlo,monospace; font-size:.92em; background:var(--card-bg); padding:0 3px; border-radius:3px; }}

.arrow {{ display:flex; align-items:center; gap:8px; color:var(--text-faint); font-size:13px; letter-spacing:.15em; margin:2px 0; }}
.arrow::before, .arrow::after {{ content:""; flex:1; height:1px; background:var(--border); }}
.divider {{ height:1px; background:var(--border); margin:5px 0; }}

.dive {{
  display:flex; gap:9px; align-items:flex-start; text-decoration:none;
  color:var(--text); page-break-inside:avoid;
}}
.dive .bullet {{ color:var(--text-faint); font-weight:700; flex-shrink:0; line-height:1.6; }}
.dive-t {{ font-size:16px; line-height:1.6; }}
.dive-t mark {{ background:var(--mark); padding:0 2px; border-radius:2px; }}
.dive-mark {{ color:var(--accent); font-weight:700; }}

.bullet.spacer {{ visibility:hidden; }}
.imgnode {{ flex:1; page-break-inside:avoid; }}
.imgnode img {{ display:block; width:100%; max-width:290px; height:auto; border-radius:10px; border:1px solid var(--border); }}
.imgnode figcaption {{ font-size:12.5px; color:var(--text-faint); margin-top:7px; line-height:1.45; }}
</style>
</head>
<body>
<div class="cover">
  <div class="kicker">PDF-прототип навигации</div>
  <h1>personality 15 — конспект как дерево</h1>
  <div class="rule"></div>
  <div class="how">
    Полный конспект курса. Чтение иерархии на телефоне.<br><br>
    <b>Тапай пункт с ▸ в конце</b> — нырнёшь вглубь, к детям этого узла.<br>
    <b>Хлебные крошки</b> сверху — путь назад: тапни любой уровень.<br><br>
    На экране всегда один узел и его прямые дети, глубже — по тапам.
  </div>
  <div class="meta">полный файл personality 15.md · {len(cards)} карточек-узлов</div>
</div>
{CARDS}
</body>
</html>'''

with open("/tmp/conspect-pdf/conspect.html", "w", encoding="utf-8") as f:
    f.write(HTML)

# ── App: впечатать дерево-JSON в шаблон аутлайнера ──
def strip_app(node):
    """Очистить дерево для app: убрать служебные id/crumb/heading, оставить структуру."""
    if node.get("divider"):
        return {"divider": True}
    if node.get("arrow"):
        return {"arrow": True}
    if node.get("img"):
        return {"img": node["img"], "caption": node.get("caption", "")}
    out = {"text": node["text"]}
    kids = [strip_app(c) for c in node.get("children", [])]
    if kids:
        out["children"] = kids
    return out
APP_TREE = strip_app(TREE)
try:
    with open(APP_TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    app_html = tpl.replace("/*__TREE__*/", json.dumps(APP_TREE, ensure_ascii=False))
    with open(APP_OUT, "w", encoding="utf-8") as f:
        f.write(app_html)
    print("app written:", APP_OUT)
except FileNotFoundError:
    print("WARN: app template not found, skipped app generation")

print(f"cards: {len(cards)}")
print("html written")
