# Teams Message Styles

## Island Style (`island`)
- **File:** `island.json`
- **Visual:** Beach background image (Unsplash), dark emphasis container overlay, readable text
- **Background URL:** `https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=30`
- **Structure:**
  - Spacer TextBlock (shows background at top)
  - Container (style=emphasis) with:
    - Header: "🌴 Coconut" (color=good, size=large, weight=bolder)
    - Content: message text (wrap=true)
    - Footer signature: right-aligned, subtle, small
  - Spacer TextBlock (shows background at bottom)
- **Footer:** Signature is OUTSIDE the card in plain HTML (`--coconut-bot 🌴`) for reaction tap target
- **Card options:** Full width (`msTeams.width: "full"`), schema v1.5
- **Buttons:** Use `ActionSet` with `Action.ShowCard` for collapsible topic sections
- **FactSet:** Use for structured key-value data within the container
- **Joel approved:** ✅ "Yes yes perfect!" + "Amazing 😍😍😍" (2026-04-22)

## Clean Style (`clean`)
- **File:** `clean.html` (HTML template, not Adaptive Card)
- **Visual:** Left green border (`#14a085`), clean white background
- **Structure:**
  ```html
  <div style="border-left:3px solid #14a085; padding:8px 14px; margin:4px 0; font-family:'Segoe UI',sans-serif; font-size:14px; line-height:1.5; color:#1a1a1a">
    {{CONTENT}}
    <br><br><i>--coconut-bot</i> 🌴
  </div>
  ```
- **Joel approved:** ✅ "I love this format" / "clean af" (2026-04-22)

## Plain Style (`plain`)
- Just raw HTML, no styling
- Signature appended as text

## Style Selection
- Per-chat config in `config.json` → `"style": "island"` or `"clean"`
- Override per-message with `--style` flag in `send_direct.py`
- Default: `clean` (unless overridden)

## Multi-Topic Card Pattern (Island)
For messages covering multiple topics, use nested containers within the main emphasis container:
```json
{
  "items": [
    { "text": "🌴 Coconut", "color": "good", "size": "large", "weight": "bolder", "type": "TextBlock" },
    { "text": "**Topic 1 Title**", "weight": "bolder", "type": "TextBlock" },
    { "text": "Topic 1 content...", "wrap": true, "type": "TextBlock" },
    { "type": "ActionSet", "actions": [
      { "type": "Action.ShowCard", "title": "▸ Topic 2 Details", "card": {
        "type": "AdaptiveCard", "body": [
          { "text": "Expandable content here", "wrap": true, "type": "TextBlock" }
        ]
      }}
    ]},
    { "type": "FactSet", "facts": [
      { "title": "Key", "value": "Value" }
    ]}
  ],
  "style": "emphasis",
  "type": "Container"
}
```
