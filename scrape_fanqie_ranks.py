import os
import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

START_CODE = 58344  # 0xE3E8
CHAR_SEQUENCE = [
    "D", "在", "主", "特", "家", "军", "然", "表", "场", "4", "要", "只", "v", "和", "?", "6", "别", "还", "g", "现", "儿", "岁", "?", "?", "此", "象", "月", "3", "出", "战", "工", "相", "o", "男", "直", "失", "世", "F", "都", "平", "文", "什", "V", "O", "将", "真", "T", "那", "当", "?", "会", "立", "些", "u", "是", "十", "张", "学", "气", "大", "爱", "两", "命", "全", "后", "东", "性", "通", "被", "1", "它", "乐", "接", "而", "感", "车", "山", "公", "了", "常", "以", "何", "可", "话", "先", "p", "i", "叫", "轻", "M", "士", "w", "着", "变", "尔", "快", "l", "个", "说", "少", "色", "里", "安", "花", "远", "7", "难", "师", "放", "t", "报", "认", "面", "道", "S", "?", "克", "地", "度", "I", "好", "机", "U", "民", "写", "把", "万", "同", "水", "新", "没", "书", "电", "吃", "像", "斯", "5", "为", "y", "白", "几", "日", "教", "看", "但", "第", "加", "候", "作", "上", "拉", "住", "有", "法", "r", "事", "应", "位", "利", "你", "声", "身", "国", "问", "马", "女", "他", "Y", "比", "父", "x", "A", "H", "N", "s", "X", "边", "美", "对", "所", "金", "活", "回", "意", "到", "z", "从", "j", "知", "又", "内", "因", "点", "Q", "三", "定", "8", "R", "b", "正", "或", "夫", "向", "德", "听", "更", "?", "得", "告", "并", "本", "q", "过", "记", "L", "让", "打", "f", "人", "就", "者", "去", "原", "满", "体", "做", "经", "K", "走", "如", "孩", "c", "G", "给", "使", "物", "?", "最", "笑", "部", "?", "员", "等", "受", "k", "行", "一", "条", "果", "动", "光", "门", "头", "见", "往", "自", "解", "成", "处", "天", "能", "于", "名", "其", "发", "总", "母", "的", "死", "手", "入", "路", "进", "心", "来", "h", "时", "力", "多", "开", "已", "许", "d", "至", "由", "很", "界", "n", "小", "与", "Z", "想", "代", "么", "分", "生", "口", "再", "妈", "望", "次", "西", "风", "种", "带", "J", "?", "实", "情", "才", "这", "?", "E", "我", "神", "格", "长", "觉", "间", "年", "眼", "无", "不", "亲", "关", "结", "0", "友", "信", "下", "却", "重", "己", "老", "2", "音", "字", "m", "呢", "明", "之", "前", "高", "P", "B", "目", "太", "e", "9", "起", "稜", "她", "也", "W", "用", "方", "子", "英", "每", "理", "便", "四", "数", "期", "中", "C", "外", "样", "a", "海", "们", "任"
]

def decode_text(text: str) -> str:
    if not text:
        return ""
    result = []
    for char in text:
        code = ord(char)
        idx = code - START_CODE
        if 0 <= idx < len(CHAR_SEQUENCE):
            result.append(CHAR_SEQUENCE[idx])
        else:
            result.append(char)
    return "".join(result)

# 我们将直接从页面解析所有新书榜类别目录，实现动态抓取

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

EXTRACT_JS = """
() => {
    const bookMap = new Map();
    const links = document.querySelectorAll('a[href^="/page/"]');
    links.forEach(link => {
        let container = link.parentElement;
        let depth = 0;
        while (container && depth < 6) {
            if (container.querySelector('img') && container.innerText.includes('在读')) {
                const href = link.getAttribute('href');
                if (!bookMap.has(href)) {
                    bookMap.set(href, container);
                }
                break;
            }
            container = container.parentElement;
            depth++;
        }
    });

    const results = [];
    for (const item of bookMap.values()) {
        let imgNode = item.querySelector('img');
        let cover = imgNode ? imgNode.getAttribute('src') : "";

        let title = "";
        if (imgNode && imgNode.getAttribute('alt')) {
            title = imgNode.getAttribute('alt').trim();
        }
        if (!title) {
            let textTitleNode = item.querySelector('h4, .title, h1') || item.querySelector('a[href^="/page/"]');
            if (textTitleNode) {
                let text = textTitleNode.innerText.trim();
                if (text && !/^\\d+$/.test(text)) {
                    title = text;
                }
            }
        }
        if (!title) title = "未知";
        if (title.includes("榜单说明")) continue;

        let authorNode = item.querySelector('.author, .author-name') || item.querySelector('a[href^="/author-page/"]');
        let author = authorNode ? authorNode.innerText.trim() : "未知";

        let reads = "未知";
        const lines = item.innerText.split('\\n');
        for (let line of lines) {
            if (line.includes('在读')) {
                reads = line;
                break;
            }
        }

        let introNode = item.querySelector('.intro, .abstract, .desc');
        let intro = introNode ? introNode.innerText.trim() : "暂无简介";

        results.push({
            title: title,
            author: author,
            reads: reads,
            intro: intro,
            cover: cover,
            url: item.querySelector('a[href^="/page/"]').getAttribute('href')
        });
    }
    return results;
}
"""

VIEW_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>番茄男频榜单对照 __DATE__</title>
<style>
  :root { color-scheme: light; }
  body { margin: 0; font-family: "Segoe UI", "PingFang SC", sans-serif; background: #f4f1ea; color: #1c1917; }
  header { padding: 20px 24px 8px; }
  h1 { margin: 0 0 6px; font-size: 22px; }
  .meta { color: #78716c; font-size: 13px; }
  .cats { display: flex; gap: 8px; flex-wrap: wrap; padding: 12px 24px 4px; position: sticky; top: 0; background: #f4f1ea; z-index: 2; }
  .cats button { border: 1px solid #d6d3d1; background: #fff; border-radius: 999px; padding: 6px 12px; cursor: pointer; }
  .cats button.active { background: #1c1917; color: #fff; border-color: #1c1917; }
  .board { padding: 8px 24px 28px; }
  .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .col { background: #fff; border-radius: 12px; padding: 12px 14px 18px; box-shadow: 0 1px 2px rgba(0,0,0,.04); }
  .col h2 { margin: 4px 0 12px; font-size: 16px; }
  .book { display: grid; grid-template-columns: 28px 1fr; gap: 8px; padding: 8px 0; border-top: 1px solid #f5f5f4; }
  .rank { color: #a8a29e; font-variant-numeric: tabular-nums; padding-top: 2px; }
  .title { font-weight: 600; text-decoration: none; color: inherit; }
  .title:hover { text-decoration: underline; }
  .sub { color: #78716c; font-size: 12px; margin-top: 2px; }
  .intro { color: #57534e; font-size: 13px; margin-top: 4px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .empty { color: #a8a29e; padding: 12px 0; }
  @media (max-width: 800px) { .cols { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<header>
  <h1>番茄男频榜单对照</h1>
  <div class="meta">日期 __DATE__ · 同一分类下，左边新书榜，右边阅读榜</div>
</header>
<div class="cats" id="cats"></div>
<div class="board"><div class="cols" id="cols"></div></div>
<script>
const DATA = __DATA__;
const byCat = new Map();
for (const cat of DATA.categories || []) {
  if (!byCat.has(cat.name)) byCat.set(cat.name, {});
  byCat.get(cat.name)[cat.board || "新书榜"] = cat.books || [];
}
const names = [...byCat.keys()];
const catsEl = document.getElementById("cats");
const colsEl = document.getElementById("cols");
function bookHtml(book, i) {
  const title = book.title || "未知";
  const href = book.url || "#";
  const reads = book.reads ? `在读 ${book.reads}` : "";
  return `<div class="book"><div class="rank">${i + 1}</div><div>
    <a class="title" href="${href}" target="_blank" rel="noreferrer">${title}</a>
    <div class="sub">${book.author || "未知"} · ${reads}</div>
    <div class="intro">${book.intro || ""}</div>
  </div></div>`;
}
function render(name) {
  document.querySelectorAll(".cats button").forEach(btn => btn.classList.toggle("active", btn.dataset.name === name));
  const boards = byCat.get(name) || {};
  colsEl.innerHTML = ["新书榜", "阅读榜"].map(board => {
    const books = boards[board] || [];
    const body = books.length ? books.map(bookHtml).join("") : `<div class="empty">这个分类还没有${board}数据</div>`;
    return `<section class="col"><h2>${board} · ${name}</h2>${body}</section>`;
  }).join("");
}
names.forEach((name, i) => {
  const btn = document.createElement("button");
  btn.textContent = name;
  btn.dataset.name = name;
  btn.onclick = () => render(name);
  catsEl.appendChild(btn);
  if (i === 0) render(name);
});
</script>
</body>
</html>
"""

def write_view(path, snapshot):
    html = VIEW_TEMPLATE.replace("__DATE__", snapshot.get("date", "")).replace(
        "__DATA__", json.dumps(snapshot, ensure_ascii=False)
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

def run_scraper(limit=30, sleep_sec=5):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    output_file = os.path.join(OUTPUT_DIR, f"fanqie_male_ranks_{date_str}.json")
    state_file = os.path.join(OUTPUT_DIR, f"task_state_{date_str}.json")
    view_file = os.path.join(OUTPUT_DIR, f"fanqie_male_ranks_{date_str}.html")

    # 男频：1_1 新书榜，1_2 阅读榜。分类 id 相同，入口用西方奇幻。
    BOARDS = [
        {"name": "新书榜", "prefix": "/rank/1_1_", "init_url": "https://fanqienovel.com/rank/1_1_1141"},
        {"name": "阅读榜", "prefix": "/rank/1_2_", "init_url": "https://fanqienovel.com/rank/1_2_1141"},
    ]
    
    # ------------- 状态恢复逻辑 -------------
    completed_cats = []
    all_categories = []  # 收集所有分类数据
    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            try:
                state = json.load(f)
                completed_cats = state.get("completed", [])
            except:
                pass
    # 如果有中断恢复的数据，先加载已有的 JSON
    if os.path.exists(output_file) and len(completed_cats) > 0:
        with open(output_file, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
                all_categories = existing.get("categories", [])
            except:
                pass
    # ----------------------------------------
    
    with sync_playwright() as p:
        if os.environ.get("GITHUB_ACTIONS"):
            browser = p.chromium.launch(headless=True)
        else:
            browser = p.chromium.launch(headless=True, channel="chrome")
        # Create a new context with a normal user agent
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        extract_js = EXTRACT_JS
        for board in BOARDS:
            board_name = board["name"]
            init_url = board["init_url"]
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在初始化并访问{board_name}：{init_url}")
            page.goto(init_url, wait_until="load", timeout=15000)
            page.wait_for_selector('a[href^="/page/"]', timeout=5000)

            categories_js = """
            (prefix) => {
                const seen = new Set();
                return Array.from(document.querySelectorAll('a'))
                    .filter(a => a.getAttribute('href') && a.getAttribute('href').includes(prefix))
                    .map(a => ({
                        name: a.innerText.trim(),
                        href: a.getAttribute('href')
                    }))
                    .filter(a => a.name && !seen.has(a.href) && seen.add(a.href));
            }
            """
            categories = page.evaluate(categories_js, board["prefix"])
            print(f"✅ {board_name}提取到 {len(categories)} 个分类。开始抓取...")

            for cat in categories:
                cat_name = cat["name"]
                cat_href = cat["href"]
                task_key = f"{board_name}/{cat_name}"

                if task_key in completed_cats:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏭️ 跳过今日已经完成抓取的类别：{task_key}")
                    continue

                print(f"[{datetime.now().strftime('%H:%M:%S')}] {board_name} -> {cat_name}")
                try:
                    page.locator(f"a[href='{cat_href}']").click()
                    time.sleep(2)
                    page.wait_for_selector('a[href^="/page/"]', timeout=5000)
                except Exception as e:
                    print(f"切换分类出错或加载超时 {task_key}: {e}")

                for _ in range(3):
                    page.evaluate("window.scrollBy(0, window.innerHeight)")
                    time.sleep(1.5)

                try:
                    books_data = page.evaluate(extract_js)
                except Exception as e:
                    print(f"执行JS抽取失败 {task_key}: {e}")
                    books_data = []

                category_books = []
                for b in books_data[:limit]:
                    t = decode_text(b.get("title", ""))
                    a = decode_text(b.get("author", ""))
                    r_raw = decode_text(b.get("reads", ""))
                    i = decode_text(b.get("intro", "")).replace("\n", " ")
                    c = b.get("cover", "")

                    if "在读" in r_raw:
                        parts = r_raw.split("在读")
                        cleaned_r = parts[1].replace(":", "").replace("：", "").strip() if len(parts) > 1 else r_raw
                    else:
                        cleaned_r = r_raw

                    category_books.append({
                        "title": t,
                        "author": a,
                        "reads": cleaned_r,
                        "intro": i,
                        "cover": c,
                        "url": "https://fanqienovel.com" + b.get("url", "")
                    })

                all_categories.append({
                    "board": board_name,
                    "name": cat_name,
                    "books": category_books
                })

                snapshot = {
                    "date": datetime.now().strftime('%Y-%m-%d'),
                    "boards": [b["name"] for b in BOARDS],
                    "categories": all_categories
                }
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(snapshot, f, ensure_ascii=False, indent=2)
                write_view(view_file, snapshot)

                completed_cats.append(task_key)
                with open(state_file, "w", encoding="utf-8") as f:
                    json.dump({"completed": completed_cats}, f, ensure_ascii=False)

                print(f"成功抓取 {task_key} 的前 {len(category_books)} 本书，且进度已存档。等待 {sleep_sec} 秒防拦截...")
                time.sleep(sleep_sec)

        browser.close()
        
    print(f"\n✅ 男频新书榜和阅读榜已抓完。数据：{output_file}")
    print(f"对照页：{view_file}")

if __name__ == "__main__":
    print("开始执行番茄男频新书榜 + 阅读榜抓取...")
    run_scraper(limit=30, sleep_sec=5)
