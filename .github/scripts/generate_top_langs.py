import os
import json
import urllib.request

USERNAME = "lohjo"
LANGS_COUNT = 6
TOKEN = os.environ.get("GITHUB_TOKEN", "")

QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    repositories(
      first: 100
      after: $after
      ownerAffiliations: [OWNER]
      isFork: false
    ) {
      pageInfo { hasNextPage endCursor }
      nodes {
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name color }
          }
        }
      }
    }
  }
}
"""


def gql(variables):
    payload = json.dumps({"query": QUERY, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def get_top_langs():
    sizes, colors = {}, {}
    after = None
    while True:
        data = gql({"login": USERNAME, "after": after})
        repos_data = data["data"]["user"]["repositories"]
        for repo in repos_data["nodes"]:
            for edge in repo["languages"]["edges"]:
                name = edge["node"]["name"]
                color = edge["node"]["color"] or "#858585"
                sizes[name] = sizes.get(name, 0) + edge["size"]
                colors[name] = color
        page = repos_data["pageInfo"]
        if not page["hasNextPage"]:
            break
        after = page["endCursor"]

    top = sorted(sizes.items(), key=lambda x: x[1], reverse=True)[:LANGS_COUNT]
    total = sum(s for _, s in top)
    return [
        {"name": n, "color": colors[n], "pct": s / total}
        for n, s in top
    ]


def svg(langs, dark):
    bg = "#21282d" if dark else "#f4f7f8"
    text_col = "#e6ebed" if dark else "#1f2a30"
    title_col = "#5fb3bd" if dark else "#0f6973"
    border_col = "#30363d" if dark else "#d0d7de"
    bar_bg = "#2d3741" if dark else "#dde3e8"

    W = 400
    PAD = 22
    bar_x = PAD
    # bar width leaves room for "100.0%" label (50px) plus gap (8px)
    bar_w = W - 2 * PAD - 58
    TITLE_H = 44
    ROW_H = 31
    BOTTOM = 12
    H = TITLE_H + len(langs) * ROW_H + BOTTOM

    font = "'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif"

    lines = [
        f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Most Used Languages">',
        f'  <title>Most Used Languages</title>',
        f'  <rect width="{W}" height="{H}" rx="6" fill="{bg}" '
        f'stroke="{border_col}" stroke-width="1"/>',
        f'  <text x="{PAD}" y="28" font-family={font!r} font-size="14" '
        f'font-weight="600" fill="{title_col}">Most Used Languages</text>',
    ]

    for i, lang in enumerate(langs):
        y = TITLE_H + i * ROW_H
        dot_cy = y + 9
        text_y = y + 13
        bar_y = y + 19
        filled = max(4.0, bar_w * lang["pct"])
        col = lang["color"]
        pct_str = f'{lang["pct"] * 100:.1f}%'
        name = lang["name"].replace("&", "&amp;").replace("<", "&lt;")

        lines += [
            f'  <circle cx="{bar_x + 5}" cy="{dot_cy}" r="5" fill="{col}"/>',
            f'  <text x="{bar_x + 14}" y="{text_y}" font-family={font!r} '
            f'font-size="11" fill="{text_col}">{name}</text>',
            f'  <text x="{W - PAD}" y="{text_y}" font-family={font!r} '
            f'font-size="11" fill="{text_col}" text-anchor="end">{pct_str}</text>',
            f'  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="7" '
            f'rx="3.5" fill="{bar_bg}"/>',
            f'  <rect x="{bar_x}" y="{bar_y}" width="{filled:.2f}" height="7" '
            f'rx="3.5" fill="{col}"/>',
        ]

    lines.append("</svg>")
    return "\n".join(lines)


if __name__ == "__main__":
    langs = get_top_langs()
    os.makedirs("dist", exist_ok=True)
    with open("dist/top-langs-dark.svg", "w", encoding="utf-8") as f:
        f.write(svg(langs, dark=True))
    with open("dist/top-langs-light.svg", "w", encoding="utf-8") as f:
        f.write(svg(langs, dark=False))
    print(f"Generated SVGs for: {', '.join(l['name'] for l in langs)}")
