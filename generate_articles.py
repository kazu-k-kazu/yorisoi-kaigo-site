#!/usr/bin/env python3
"""CareSpace 記事自動生成スクリプト"""

import anthropic, json, re, time
from datetime import datetime
from pathlib import Path

API_KEY      = "YOUR_ANTHROPIC_API_KEY"
BASE_DIR     = Path(__file__).parent
ARTICLES_DIR = BASE_DIR / "articles"
INDEX_FILE   = BASE_DIR / "articles_index.json"
ARTICLES_DIR.mkdir(exist_ok=True)

TOPICS = [
    {"category":"sudden",   "cat_label":"介護が突然始まった",   "keyword":"介護 突然 始まった 最初 何をすべき",      "title":"親の介護が突然始まった時、最初にすべき5つのこと"},
    {"category":"sudden",   "cat_label":"介護が突然始まった",   "keyword":"介護認定 申請 方法 手順",                 "title":"介護認定の申請方法と審査の流れをわかりやすく解説"},
    {"category":"dementia", "cat_label":"認知症の悩み",         "keyword":"認知症 初期症状 チェック 見分け方",       "title":"認知症の初期症状チェックリスト：早期発見のポイント"},
    {"category":"dementia", "cat_label":"認知症の悩み",         "keyword":"認知症 徘徊 対策 防止 見守り",            "title":"認知症の徘徊対策：家でできる予防と見守りの方法"},
    {"category":"dementia", "cat_label":"認知症の悩み",         "keyword":"認知症 接し方 怒らせない コツ",           "title":"認知症の親への接し方：怒らせない・傷つけないコツ"},
    {"category":"cost",     "cat_label":"介護とお金",           "keyword":"介護費用 月いくら 平均 在宅 施設",        "title":"介護にかかる費用の平均：在宅介護・施設介護で比較"},
    {"category":"cost",     "cat_label":"介護とお金",           "keyword":"介護保険 使い方 サービス 種類",           "title":"介護保険の使い方完全ガイド：使えるサービスと申請方法"},
    {"category":"cost",     "cat_label":"介護とお金",           "keyword":"高額介護サービス費 申請 戻ってくる",      "title":"高額介護サービス費とは？申請すれば費用が戻ってくる"},
    {"category":"facility", "cat_label":"施設入居を考えている", "keyword":"老人ホーム 種類 違い 特養 有料 選び方",   "title":"老人ホームの種類と違い：特養・有料・グループホームを比較"},
    {"category":"facility", "cat_label":"施設入居を考えている", "keyword":"特養 入居 条件 待機 申し込み",            "title":"特別養護老人ホームの入居条件と申し込み・待機の現実"},
    {"category":"facility", "cat_label":"施設入居を考えている", "keyword":"老人ホーム 見学 チェックポイント 選ぶ",   "title":"老人ホーム見学で確認すべき15のチェックポイント"},
    {"category":"work",     "cat_label":"介護と仕事の両立",     "keyword":"介護休業 取り方 給付金 条件",             "title":"介護休業の取り方と給付金：知らないと損する制度"},
    {"category":"work",     "cat_label":"介護と仕事の両立",     "keyword":"介護離職 後悔 しない 方法 両立",          "title":"介護離職を後悔しないために：仕事を続けながら介護する方法"},
    {"category":"burnout",  "cat_label":"介護疲れ・燃え尽き",   "keyword":"介護疲れ 解消 休む 方法 レスパイト",      "title":"介護疲れを解消する方法：上手に休むためのレスパイトケア"},
    {"category":"burnout",  "cat_label":"介護疲れ・燃え尽き",   "keyword":"施設 入れる 罪悪感 なくす 考え方",        "title":"親を施設に入れる罪悪感を手放すための考え方"},
]

def build_prompt(topic):
    return f"""あなたは介護・福祉に関する専門的なウェブライターです。
以下の条件でSEO記事を作成してください。

【記事タイトル】{topic['title']}
【メインキーワード】{topic['keyword']}
【カテゴリ】{topic['cat_label']}

【条件】
- 文字数: 1500〜2000文字
- 介護をしている家族に寄り添った、温かく実用的なトーン
- 具体的な制度・手続き・費用の情報を盛り込む
- 見出しはH2（##）とH3（###）で構造化する
- 最後に「まとめ」セクションを入れる
- 医療・法律アドバイスは避け「専門家・地域窓口にご相談を」と誘導する
- 末尾に「本記事は医療・法律アドバイスではありません」を記載

【出力形式】Markdown形式（H1タイトルは不要）
"""

def md_to_html(md_text):
    html = md_text
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'^[-・] (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*</li>\n?)+', lambda m: f'<ul>\n{m.group()}</ul>\n', html)
    paragraphs = []
    for para in html.split('\n\n'):
        para = para.strip()
        if not para: continue
        paragraphs.append(para if para.startswith('<h') or para.startswith('<ul') else f'<p>{para}</p>')
    return '\n'.join(paragraphs)

def save_article_html(topic, content_md, slug):
    content_html = md_to_html(content_md)
    now_str = datetime.now().strftime('%Y年%m月%d日')
    cat_colors = {"sudden":"#DD6B20","dementia":"#9F7AEA","cost":"#38B2AC","facility":"#4299E1","work":"#48BB78","burnout":"#F56565"}
    color = cat_colors.get(topic['category'], "#DD6B20")
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{topic['title']} | CareSpace</title>
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family:'Hiragino Sans','Yu Gothic',sans-serif; background:#FFFAF0; color:#2D3748; line-height:1.8; }}
    nav {{ background:#fff; border-bottom:1px solid #E2E8F0; padding:0 40px; height:64px; display:flex; align-items:center; justify-content:space-between; position:sticky; top:0; z-index:100; }}
    .logo {{ font-size:20px; font-weight:700; color:#2D3748; text-decoration:none; }}
    .logo span {{ color:#DD6B20; }}
    .back-link {{ color:#DD6B20; text-decoration:none; font-size:14px; }}
    .container {{ max-width:780px; margin:48px auto; padding:0 24px; }}
    .cat-tag {{ display:inline-block; background:{color}1a; color:{color}; font-size:12px; font-weight:600; padding:4px 12px; border-radius:20px; margin-bottom:12px; }}
    h1 {{ font-size:30px; font-weight:700; color:#1A202C; line-height:1.4; margin-bottom:12px; }}
    .article-meta {{ font-size:13px; color:#718096; margin-bottom:32px; }}
    .article-body {{ background:#fff; border-radius:16px; padding:40px; box-shadow:0 2px 12px rgba(45,55,72,0.06); }}
    .article-body h2 {{ font-size:22px; font-weight:700; margin:36px 0 14px; padding-left:14px; border-left:4px solid {color}; }}
    .article-body h3 {{ font-size:17px; font-weight:700; color:#4A5568; margin:24px 0 10px; }}
    .article-body p {{ margin-bottom:16px; font-size:15px; }}
    .article-body ul {{ margin:12px 0 20px 24px; }}
    .article-body li {{ margin-bottom:8px; font-size:15px; }}
    .disclaimer {{ background:#FFFBEB; border:1px solid #F6E05E; border-radius:8px; padding:16px 20px; margin-top:32px; font-size:13px; color:#744210; }}
    .cta-box {{ background:linear-gradient(135deg,#744210,#C05621); border-radius:12px; padding:24px; margin-top:32px; text-align:center; }}
    .cta-box p {{ color:#FBD38D; font-size:13px; margin-bottom:12px; }}
    .cta-btn {{ background:#DD6B20; color:#fff; padding:12px 28px; border-radius:8px; text-decoration:none; font-weight:600; font-size:14px; display:inline-block; }}
    footer {{ text-align:center; padding:48px; color:#A0AEC0; font-size:13px; margin-top:48px; }}
  </style>
</head>
<body>
  <nav><a href="../index.html" class="logo">Care<span>Space</span></a><a href="../index.html" class="back-link">← トップに戻る</a></nav>
  <div class="container">
    <span class="cat-tag">{topic['cat_label']}</span>
    <h1>{topic['title']}</h1>
    <div class="article-meta">公開日: {now_str} ｜ キーワード: {topic['keyword']}</div>
    <div class="article-body">
      {content_html}
      <div class="disclaimer">※ 本記事は医療・法律アドバイスではありません。お住まいの市区町村窓口や専門家にご相談ください。</div>
      <div class="cta-box"><p>もっと詳しく相談したい方へ</p><a href="../chat.html" class="cta-btn">AIに無料相談する</a></div>
    </div>
  </div>
  <footer>© 2026 CareSpace. All rights reserved.</footer>
</body>
</html>"""
    out_path = ARTICLES_DIR / f"{slug}.html"
    out_path.write_text(html, encoding='utf-8')
    return out_path

def main():
    client = anthropic.Anthropic(api_key=API_KEY)
    index = json.loads(INDEX_FILE.read_text(encoding='utf-8')) if INDEX_FILE.exists() else []
    existing_slugs = {e['slug'] for e in index}
    print('\n' + '='*50 + '\n  CareSpace 記事自動生成\n' + '='*50)
    generated = skipped = 0
    for i, topic in enumerate(TOPICS, 1):
        slug = f"{topic['category']}-{i:03d}"
        if slug in existing_slugs:
            print(f'  [{i:02d}/{len(TOPICS)}] スキップ: {topic["title"][:35]}'); skipped += 1; continue
        print(f'  [{i:02d}/{len(TOPICS)}] 生成中: {topic["title"][:40]}')
        try:
            response = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=3000,
                messages=[{"role":"user","content":build_prompt(topic)}])
            content_md = response.content[0].text
            out_path = save_article_html(topic, content_md, slug)
            index.append({"slug":slug,"title":topic['title'],"category":topic['category'],"cat_label":topic['cat_label'],"keyword":topic['keyword'],"file":f"articles/{slug}.html","created_at":datetime.now().isoformat()})
            INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
            existing_slugs.add(slug)
            print(f'         → 保存: {out_path.name}'); generated += 1; time.sleep(1)
        except Exception as e:
            print(f'         → エラー: {e}')
    print(f'\n  完了: {generated}件生成 / {skipped}件スキップ\n')

if __name__ == '__main__':
    main()
