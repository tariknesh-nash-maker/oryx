def _section(text):
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}

def _divider():
    return {"type": "divider"}

def build_blocks(title: str, digest: dict):
    """
    digest = {
      "countries": [{"name":"Benin","items":["• …","• …"]}, ...],
      "subregional": ["• …"],
      "international": ["• …"],
      "analysis": {
        "opportunities":[
          {"title":"…","relevance":"High","ambition":"Med","likelihood":"High","time":"Low","note":"…"}
        ],
        "top_pick":"…"
      }
    }
    """
    blocks = [
        _section(f"*{title}*"),
        _divider(),
        _section("*Country updates (past 24h)*"),
    ]

    non_empty = [c for c in digest["countries"] if c["items"]]
    empty = [c for c in digest["countries"] if not c["items"]]
    ordered = non_empty + empty

    for c in ordered:
        bullets = "\n".join(c["items"]) if c["items"] else "_No verified items in the past 24h._"
        blocks += [_section(f"*{c['name']}*\n{bullets}"), _divider()]

    if digest.get("subregional"):
        blocks += [_section("*Subregional*"), _section("\n".join(digest["subregional"])), _divider()]
    if digest.get("international"):
        blocks += [_section("*International*"), _section("\n".join(digest["international"])), _divider()]

    blocks += [_section("*Assistant team analysis — decision matrix*")]
    if digest["analysis"].get("opportunities"):
        for i, opp in enumerate(digest["analysis"]["opportunities"], 1):
            line = (
                f"*{i}. {opp['title']}*\n"
                f"• Relevance: {opp['relevance']}  "
                f"• Ambition: {opp['ambition']}  "
                f"• Likelihood: {opp['likelihood']}  "
                f"• Time cost: {opp['time']}\n"
                f"_Note_: {opp.get('note','—')}"
            )
            blocks += [_section(line)]
    else:
        blocks += [_section("_No high-signal opportunities today._")]

    blocks += [_divider(), _section(f"*Single most promising opportunity*: {digest['analysis']['top_pick']}")]
    return blocks

