import os
base = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(base, 'logo7.svg')
# Color to match logo8.jpg - change this hex to match your reference image
FILL_COLOR = "#7ab8e0"  # App primary blue; replace with exact hex from logo8.jpg if needed

with open(path) as f:
    s = f.read()

defs_end = s.find('</defs>')
main = s[defs_end:]
img_start = main.find('<image x="0" y="0" width="7373"')
if img_start == -1:
    print("Main image not found")
    exit(1)
tag_start = defs_end + img_start
rest = s[tag_start:]
end = rest.find('height="7373"')
end = rest.find('/>', end)
if end == -1:
    print("Image tag end not found")
    exit(1)
old_tag = rest[: end + 2]  # include "/>"
new_rect = '<rect x="0" y="0" width="7373" height="7373" fill="' + FILL_COLOR + '"/>'
new_s = s[:tag_start] + new_rect + rest[end + 2:]
with open(path, 'w') as f:
    f.write(new_s)
print("Done. Replaced logo image with solid fill:", FILL_COLOR)
