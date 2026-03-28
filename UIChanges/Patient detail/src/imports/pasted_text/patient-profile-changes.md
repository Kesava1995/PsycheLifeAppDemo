Apply these 8 specific changes to the Patient Profile Page. Do not change anything not mentioned.
CHANGE 1 — Equal 50/50 split:

Left panel: exactly 50% viewport width
Right panel: exactly 50% viewport width
Both panels: full viewport height minus navbar, overflow-y scroll
Gap: 0 between panels, 1px solid #e4ecec vertical divider only

CHANGE 2 — Hide scrollbars:

Both panels: scrollbar completely hidden visually but fully functional
CSS: scrollbar-width: none (Firefox) + ::-webkit-scrollbar { display: none } (Chrome/Safari)
Scroll behaviour unchanged — only the visible scrollbar track removed

CHANGE 3 — Background Factors badge structure:

Each background factor (Premorbid Personality, ACE, Family History etc.) is an outer container card:

Background #ffffff, border 1px solid #e4ecec, border-radius 12px, padding 12px 14px
Outer cards placed side by side in a wrapping row, gap 10px
Each outer card grows vertically downward if inner chips overflow


Outer card header: category name Inter 600 13px #3f4948, margin-bottom 8px
Inner findings as chips: background #e4ecec, color #006672, Inter 500 12px, padding 4px 10px, border-radius 999px, gap 6px, flex-wrap wrap
Example: outer card "Premorbid Personality" contains chips "Anxious" "Introverted" "Perfectionistic"

CHANGE 4 — Smooth scroll fix:

Both panel containers: scroll-behavior: smooth
Remove any overflow: hidden on parent containers that may clip scroll
Add -webkit-overflow-scrolling: touch for smooth momentum scrolling on tablet
Ensure no transform or will-change on scrolling containers that cause paint glitches

CHANGE 5 — Action buttons:

Remove Dashboard button completely
Rename "Life Chart" button to "View Life Chart" — keep same teal style
Only two buttons remain: "View Life Chart" (#006672) and "Add Follow-up" (#181c1d)
Both full width, equal height, gap 10px, Manrope 600 14px

CHANGE 6 — Tags section (add below email, above Notes):

Section header row: "Tags" Inter 600 13px #3f4948 uppercase letter-spacing 0.05em + small pencil ✏️ icon right-aligned, cursor pointer
Default state (view mode):

Tags displayed as chips: background #e4ecec, color #006672, Inter 500 13px, padding 5px 12px, border-radius 999px
Each chip starts with # symbol: e.g. "#HighRisk" "#VIP" "#NonCompliant"
Chips in a wrapping row, gap 8px
Empty state: "No tags added" Inter 400 12px #9aacae italic


Edit mode (pencil clicked):

Each chip gains a small × on right side — clicking × removes that chip immediately
A "+" button appears after last chip: teal circle 20px, white +
Clicking "+": a searchable dropdown appears — search bar + predefined options:

High Risk, Non-compliant, VIP, Research Participant, Needs Follow-up, Treatment Resistant, Good Prognosis, Requires Interpreter, Medico-legal, Others (free type)


Selecting an option adds it as a new chip instantly
Clicking ✏️ again exits edit mode, × marks disappear



CHANGE 7 — Send Custom Message (add below Tags):

A full-width button: "✉️ Send Custom Message" — background #f8fafa, border 1.5px solid #e4ecec, border-radius 10px, padding 12px 16px, Inter 600 13px #181c1d, cursor pointer, text-align centre
On click: expands below the button (smooth max-height animation 200ms):

Two channel selector cards side by side, gap 10px:

WhatsApp card: background #f0fdf4, border 1.5px solid #86efac, border-radius 10px, padding 12px, text-align centre, Inter 600 13px #166534, cursor pointer — icon 💬
Gmail card: background #fef2f2, border 1.5px solid #fca5a5, border-radius 10px, same size, Inter 600 13px #991b1b, cursor pointer — icon 📧
Selected card: border 2px solid its colour, slight background deepening


After selecting channel — compose area appears below (smooth expand):

To: field (pre-filled with patient contact) — read-only, Inter 400 13px
Subject (Gmail only): text input, Inter 400 13px, ghost border
Message: textarea 4 rows, Inter 400 14px, border-radius 8px, ghost border
Placeholder: "Type your message here..."
Quick template pills below textarea: "Appointment reminder" "Follow-up reminder" "Lab report ready" "Custom" — clicking inserts template text
Send button: full width, background #006672, white, Inter 600 13px, border-radius 8px, padding 10px
Cancel link: Inter 400 13px #3d5050, centred below Send





CHANGE 8 — Notes as checklist:

Each note displayed as a checklist item:

Layout: display: flex; align-items: flex-start; gap: 10px
Left: checkbox — 16px × 16px, border-radius 4px, border 1.5px solid #bdc8cb, background white, cursor pointer
Checked state: background #006672, border-color #006672, white checkmark ✓ inside
Right (flex column):

Date: Inter 600 12px #006672
Note text: Inter 400 13px #181c1d
When checked: note text gets text-decoration: line-through, color fades to #9aacae


Each note: background #f8fafa, border-radius 8px, padding 10px 14px, margin-bottom 8px
Transition: 150ms for checkbox fill + strikethrough


"+" button unchanged — still opens date + note modal as before