import json
import xml.etree.ElementTree as ET
from pathlib import Path

SRC = Path("source.vstheme")
OUT = Path("src/vstheme-tokens.json")


def read_slot(color, slot_name):
    slot = color.find(slot_name)
    if slot is None:
        return None

    return {
        "type": slot.attrib.get("Type"),
        "source": slot.attrib.get("Source"),
        "valid": slot.attrib.get("Type") != "CT_INVALID",
    }


tree = ET.parse(SRC)
root = tree.getroot()

theme = root.find("Theme")
if theme is None:
    raise ValueError("No <Theme> element found")

categories = []

for category in theme.findall("Category"):
    current = {
        "name": category.attrib["Name"],
        "guid": category.attrib["GUID"],
        "colors": [],
    }

    for color in category.findall("Color"):
        current["colors"].append(
            {
                "name": color.attrib["Name"],
                "background": read_slot(color, "Background"),
                "foreground": read_slot(color, "Foreground"),
            }
        )

    categories.append(current)

OUT.write_text(json.dumps(categories, indent=2), encoding="utf-8")

print(
    "wrote vstheme-tokens.json:",
    len(categories),
    "categories",
    sum(len(c["colors"]) for c in categories),
    "colors",
)
