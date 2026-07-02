# -*- coding: utf-8 -*-
"""Generate generated.vstheme from vstheme-tokens.json.

The token JSON is expected to have this shape:

[
  {
    "name": "Text Editor Text Manager Items",
    "guid": "{...}",
    "colors": [
      {
        "name": "Plain Text",
        "background": {"type": "CT_RAW", "source": "FF181818", "valid": true},
        "foreground": {"type": "CT_RAW", "source": "FFE4E4EF", "valid": true}
      }
    ]
  }
]

The source theme is used as a token/slot skeleton only. Valid raw colour slots are
remapped to gruber-darker roles. Invalid, automatic, colour-index and system-colour
slots are preserved because they are not literal RGB colours.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
TOKENS_PATH = os.path.join(HERE, "vstheme-tokens.json")
OUTPUT_PATH = os.path.join(HERE, "generated.vstheme")

THEME_NAME = "Gruber Darker"
THEME_GUID = "{ce2c3040-574d-486e-bd24-2f98fb725702}"
# Visual Studio Dark base theme. Safe to remove if you do not want a base theme.
BASE_GUID = "{1ded0138-47ce-435e-84ef-9ec1f439b749}"

# ---------------------------------------------------------------------------
# gruber-darker-theme.el palette
# ---------------------------------------------------------------------------
PALETTE = {
    "bg-1": "101010",
    "bg": "181818",
    "bg+1": "282828",
    "bg+2": "453D41",
    "bg+3": "484848",
    "bg+4": "52494E",
    "fg": "E4E4EF",
    "fg+1": "F4F4FF",
    "fg+2": "F5F5F5",
    "white": "FFFFFF",
    "black": "000000",
    "red-1": "C73C3F",
    "red": "F43841",
    "red+1": "FF4F58",
    "green": "73C936",
    "yellow": "FFDD33",
    "brown": "CC8C3C",
    "quartz": "95A99F",
    "niagara-2": "303540",
    "niagara-1": "565F73",
    "niagara": "96A6C8",
    "wisteria": "9E95C7",
}

PALETTE_BY_RGB = {value.upper(): key for key, value in PALETTE.items()}


def argb(key: str, alpha: str = "FF") -> str:
    return alpha.upper() + PALETTE[key].upper()


def split_argb(source: str | None) -> tuple[str, str]:
    source = (source or "FF000000").upper()
    if len(source) == 6:
        return "FF", source
    if len(source) != 8:
        return "FF", "000000"
    return source[:2], source[2:]


def preserve_alpha(source: str | None, role: str) -> str:
    alpha, _ = split_argb(source)
    return argb(role, alpha)


@dataclass(frozen=True)
class SlotResult:
    type: str
    source: str


# ---------------------------------------------------------------------------
# Exact semantic overrides. These are the tokens where the Visual Studio name
# maps cleanly to the original gruber-darker faces.
# ---------------------------------------------------------------------------
EXACT: dict[tuple[str | None, str], tuple[str | None, str | None]] = {
    # Text editor surface
    ("Text Editor Text Manager Items", "Plain Text"): ("fg", "bg"),
    ("Text Editor Text Manager Items", "Selected Text"): (None, "bg+3"),
    ("Text Editor Text Manager Items", "Inactive Selected Text"): (None, "bg+3"),
    ("Text Editor Text Manager Items", "Indicator Margin"): (None, "bg"),
    ("Text Editor Text Manager Items", "Visible Whitespace"): ("bg+1", None),

    # Common editor-like windows
    ("Command Window", "Plain Text"): ("fg", "bg"),
    ("Command Window", "Selected Text"): (None, "bg+3"),
    ("Command Window", "Inactive Selected Text"): (None, "bg+3"),
    ("Immediate Window", "Plain Text"): ("fg", "bg"),
    ("Output Window", "Plain Text"): ("fg", "bg"),
    ("FSharpInteractive", "Plain Text"): ("fg", "bg"),

    # Text Editor Language Service Items
    ("Text Editor Language Service Items", "Comment"): ("brown", None),
    ("Text Editor Language Service Items", "Identifier"): ("fg", None),
    ("Text Editor Language Service Items", "Keyword"): ("yellow", None),
    ("Text Editor Language Service Items", "Number"): ("wisteria", None),
    ("Text Editor Language Service Items", "Operator"): ("fg", None),
    ("Text Editor Language Service Items", "Preprocessor Keyword"): ("quartz", None),
    ("Text Editor Language Service Items", "String"): ("green", None),
    ("Text Editor Language Service Items", "String(C# @ Verbatim)"): ("green", None),
    ("Text Editor Language Service Items", "User Types"): ("quartz", None),
    ("Text Editor Language Service Items", "User Types(Delegates)"): ("quartz", None),
    ("Text Editor Language Service Items", "User Types(Enums)"): ("quartz", None),
    ("Text Editor Language Service Items", "User Types(Interfaces)"): ("quartz", None),
    ("Text Editor Language Service Items", "User Types(Type parameters)"): ("quartz", None),
    ("Text Editor Language Service Items", "User Types(Value types)"): ("quartz", None),
    ("Text Editor Language Service Items", "Excluded Code"): ("niagara-1", None),
    ("Text Editor Language Service Items", "Stale Code"): ("quartz", "bg+3"),
    ("Text Editor Language Service Items", "Error"): ("red+1", None),

    # High-value environment tokens
    ("Environment", "Window"): ("fg", "bg"),
    ("Environment", "EnvironmentBackground"): (None, "bg"),
    ("Environment", "ToolWindowBackground"): (None, "bg"),
    ("Environment", "ToolWindowText"): ("fg", None),
    ("Environment", "ToolWindowBorder"): (None, "bg+1"),
    ("Environment", "PanelText"): ("fg", None),
    ("Environment", "PanelHyperlink"): ("niagara", None),
    ("Environment", "PanelHyperlinkHover"): ("wisteria", None),
    ("Environment", "CommandBarTextActive"): ("fg+1", None),
    ("Environment", "CommandBarTextInactive"): ("niagara-1", None),
    ("Environment", "CommandBarMenuLinkText"): ("niagara", None),
    ("Environment", "CommandBarMenuWatermarkText"): ("quartz", None),
}

SLOT_EXACT: dict[tuple[str, str, str], str] = {
    # XAML / XML core markup.
    ("Text Editor Language Service Items", "XAML Name", "Foreground"): "yellow",
    ("Text Editor Language Service Items", "XAML Keyword", "Foreground"): "yellow",
    ("Text Editor Language Service Items", "XAML Delimiter", "Foreground"): "niagara",
    ("Text Editor Language Service Items", "XAML Attribute", "Foreground"): "quartz",
    ("Text Editor Language Service Items", "XAML Attribute Quotes", "Foreground"): "green",
    ("Text Editor Language Service Items", "XAML Attribute Value", "Foreground"): "green",
    ("Text Editor Language Service Items", "XAML Text", "Foreground"): "fg",
    ("Text Editor Language Service Items", "XAML Comment", "Foreground"): "brown",
    ("Text Editor Language Service Items", "XAML CData Section", "Foreground"): "green",
    ("Text Editor Language Service Items", "XAML Processing Instruction", "Foreground"): "quartz",

    # XAML markup extensions: {Binding Left.Name, UpdateSourceTrigger=PropertyChanged}
    ("Text Editor Language Service Items", "XAML Markup Extension Class", "Foreground"): "yellow",
    ("Text Editor Language Service Items", "XAML Markup Extension Parameter Name", "Foreground"): "fg+1",
    ("Text Editor Language Service Items", "XAML Markup Extension Parameter Value", "Foreground"): "fg+1",

    # XML equivalents.
    ("Text Editor Language Service Items", "XML Name", "Foreground"): "yellow",
    ("Text Editor Language Service Items", "XML Keyword", "Foreground"): "yellow",
    ("Text Editor Language Service Items", "XML Delimiter", "Foreground"): "niagara",
    ("Text Editor Language Service Items", "XML Attribute", "Foreground"): "quartz",
    ("Text Editor Language Service Items", "XML Attribute Quotes", "Foreground"): "green",
    ("Text Editor Language Service Items", "XML Attribute Value", "Foreground"): "green",
    ("Text Editor Language Service Items", "XML Text", "Foreground"): "fg",
    ("Text Editor Language Service Items", "XML Comment", "Foreground"): "brown",
    ("Text Editor Language Service Items", "XML CData Section", "Foreground"): "green",
    ("Text Editor Language Service Items", "XML Processing Instruction", "Foreground"): "quartz",
    ("Text Editor Language Service Items", "XML Doc Attribute", "Foreground"): "quartz",
    ("Text Editor Language Service Items", "XML Doc Tag", "Foreground"): "yellow",
    ("Text Editor Language Service Items", "XML Doc Comment", "Foreground"): "brown",

    # MEF / editor classification fallbacks.
    ("Text Editor MEF Items", "XmlNameClassificationFormat", "Foreground"): "yellow",
    ("Text Editor MEF Items", "XmlDelimiterClassificationFormat", "Foreground"): "niagara",
    ("Text Editor MEF Items", "XmlAttributeNameClassificationFormat", "Foreground"): "quartz",
    ("Text Editor MEF Items", "XmlAttributeQuotesClassificationFormat", "Foreground"): "green",
    ("Text Editor MEF Items", "XmlAttributeValueClassificationFormat", "Foreground"): "green",
    ("Text Editor MEF Items", "XmlTextClassificationFormat", "Foreground"): "fg",
    ("Text Editor MEF Items", "XmlCommentClassificationFormat", "Foreground"): "brown",
    ("Text Editor MEF Items", "XmlCDataSectionClassificationFormat", "Foreground"): "green",
    ("Text Editor MEF Items", "XmlProcessingInstructionClassificationFormat", "Foreground"): "quartz",
    ("Text Editor MEF Items", "XmlDocAttributeClassificationFormat", "Foreground"): "quartz",
    ("Text Editor MEF Items", "XmlDocTagClassificationFormat", "Foreground"): "yellow",
    ("Text Editor MEF Items", "XmlDocCommentClassificationFormat", "Foreground"): "brown",

    ("Text Editor MEF Items", "Markup Node", "Foreground"): "yellow",
    ("Text Editor MEF Items", "Markup Attribute", "Foreground"): "quartz",
    ("Text Editor MEF Items", "Markup Attribute Value", "Foreground"): "green",

    ("Text Editor MEF Items", "axml - name", "Foreground"): "yellow",
    ("Text Editor MEF Items", "axml - delimiter", "Foreground"): "niagara",
    ("Text Editor MEF Items", "axml - attribute name", "Foreground"): "quartz",
    ("Text Editor MEF Items", "axml - attribute quotes", "Foreground"): "green",
    ("Text Editor MEF Items", "axml - attribute value", "Foreground"): "green",
    ("Text Editor MEF Items", "axml - text", "Foreground"): "fg",
    ("Text Editor MEF Items", "axml - comment", "Foreground"): "brown",
    ("Text Editor MEF Items", "axml - cdata section", "Foreground"): "green",
    ("Text Editor MEF Items", "axml - processing instruction", "Foreground"): "quartz",
    ("Text Editor MEF Items", "axml - entity reference", "Foreground"): "niagara",
}

# Name-only fallbacks for small debugger panes and repeated names.
NAME_EXACT: dict[str, tuple[str | None, str | None]] = {
    "Plain Text": ("fg", "bg"),
    "Text": ("fg", None),
    "SelectedText": ("fg+1", "bg+3"),
    "Selected Text": (None, "bg+3"),
    "Inactive Selected Text": (None, "bg+3"),
    "ChangedText": ("red", None),
    "Changed Text": ("red", None),
    "LinkLabel": ("niagara", None),
    "Hyperlink": ("niagara", None),
    "HyperlinkMouseOver": ("wisteria", None),
    "Line Number": ("bg+4", None),
    "Selected Line Number": ("fg+1", None),
    "CurrentLineActiveFormat": (None, "bg+1"),
    "CurrentLineInactiveFormat": (None, "bg"),
    "Caret (Primary)": ("fg+2", None),
    "Caret (Secondary)": ("quartz", None),
}

# Ordered foreground roles. Earlier patterns win.
FOREGROUND_PATTERNS: list[tuple[str, str]] = [
    # Specific XML / Razor / web classifications.
    (r"\b(cdata|xml cdata|xaml cdata|xmlcdata|xml cdata section|xaml cdata section)\b", "quartz"),
    (r"\b(processing instruction|doc tag|xml doc tag|xml doc|documentation tag)\b", "quartz"),
    (r"\b(embedded expression|xml embedded expression|razor transition|razor component|razor component element)\b", "yellow"),
    (r"\b(html server-side script|server-side script)\b", "yellow"),

    # SQL / command-language classifications.
    (r"\b(sql stored procedure|stored procedure)\b", "niagara"),
    (r"\b(sql system table|system table)\b", "quartz"),
    (r"\b(sqlcmd command|sql command|script command)\b", "yellow"),

    # C++ / semantic token classifications.
    (r"\b(cpp event|event semantic|event semantic token)\b", "niagara"),
    (r"\b(cpp udl raw|udl raw|raw semantic token)\b", "green"),
    (r"\b(cpp new delete|new delete)\b", "red"),
    (r"\b(cpp attributes|attributes syntactic|attribute syntactic)\b", "quartz"),

    # Editor/test/log/tooling classifications.
    (r"\b(build head|buildhead)\b", "yellow"),
    (r"\b(user keyword|user keywords)\b", "yellow"),
    (r"\b(memory address|memory data|register data|address|register)\b", "wisteria"),
    (r"\b(unreadable|nat)\b", "red+1"),
    (r"\b(find results|search term|filename|file name|current list location)\b", "niagara"),
    (r"\b(log information|information)\b", "niagara"),
    (r"\b(log custom|logcustom)\d*\b", "quartz"),
    (r"\b(inline hints|inline hint|hinted suggestion)\b", "niagara-1"),
    (r"\b(regular expression|regex|regex grouping|self escaped|other escape|regex self escaped|regex other escape)\b", "wisteria"),
    (r"\b(urlformat|url format)\b", "niagara"),
    (r"\b(tracepoint|breakpoint|logpoint|snappoint)\b", "fg+1"),
    (r"\b(coverage touched)\b", "green"),
    (r"\b(coverage partially touched)\b", "yellow"),
    (r"\b(coverage not touched)\b", "red"),
    (r"\b(file line|source line|instruction line|symbol line|symbol definition|symbol reference)\b", "niagara"),
    (r"\b(navigable symbol|symbol)\b", "niagara"),
    (r"\b(current statement|executing thread|instruction pointer|call return)\b", "fg+1"),
    (r"\b(sampling hot line)\s*[1-5]\b", "yellow"),
    (r"\b(smart tag|task list shortcut|rename tracking|fixup tag)\b", "quartz"),
    (r"\b(stale code|edit and continue|inline diagnostics)\b", "quartz"),
    (r"\b(test summary|test summary default|test summary stack|test summary diagnostic|test summary no source)\b", "quartz"),

    # Diagnostics / state.
    (r"\b(error|invalid|unparsed|conflict|mismatch|failed|failure|critical)\b", "red+1"),
    (r"\b(warning|caution|alert)\b", "yellow"),
    (r"\b(deleted|removed|remove|deletion|del)\b", "red-1"),
    (r"\b(changed|modified|modification|track reverted)\b", "red"),
    (r"\b(add|adds|addition|additions|added|accepted|success|resolved|passed|pass|ok|status ok)\b", "green"),
    (r"\b(pending|status pending)\b", "yellow"),

    # Core syntax mapping to Gruber Darker.
    (r"\b(comment|comments|documentation|doc comment)\b", "brown"),
    (r"\b(string|literal|verbatim)\b", "green"),
    (r"\b(keyword|directive|control keyword|script keyword)\b", "yellow"),
    (r"\b(number|numeric|constant|enum member)\b", "wisteria"),
    (r"\b(preprocessor|preprocess|macro|builtin|built-in|built in|script preprocess)\b", "quartz"),
    (r"\b(type parameter|typeparam|generic type)\b", "quartz"),
    (r"\b(class|struct|interface|enum|delegate|record|module|ref type|value type|user type|typename|type)\b", "quartz"),
    (r"\b(function|method|member function|extension method|constructor|mixin|printf)\b", "niagara"),
    (r"\b(namespace|tag helper|element name|xml name|html element|markup node|selector|entity|url|link|hyperlink)\b", "niagara"),
    (r"\blabel\b", "niagara"),

    # XAML / XML / markup
    # Goal:
    #   <TextBlock Text="Hello" />
    #    ^ yellow   ^ quartz ^ green
    #
    #   Text="{Binding Left.Name, UpdateSourceTrigger=PropertyChanged}"
    #         ^ green quote
    #          ^ blue {
    #           ^ yellow Binding
    #                   ^ white Left.Name
    #                            ^ blue ,
    #                              ^ white UpdateSourceTrigger
    #                                                 ^ blue =
    #                                                  ^ quartz PropertyChanged
    #                                                                 ^ blue }
    #                                                                  ^ green quote

    # Tag / element names.
    (r"\b(xaml|xml|axml)\s+(name|keyword)\b", "yellow"),
    (r"\b(xmlnameclassificationformat|xml name classification format)\b", "yellow"),
    (r"\b(xml literal|xml doc comment|axml)\s*-\s*name\b", "yellow"),
    (r"\b(html element name|markup node|razor component element|razor tag helper element)\b", "yellow"),

    # Tag / markup delimiters: < > / =
    (r"\b(xaml|xml|axml)\s+delimiter\b", "niagara"),
    (r"\b(xmldelimiterclassificationformat|xml delimiter classification format)\b", "niagara"),
    (r"\b(xml literal|xml doc comment|axml)\s*-\s*delimiter\b", "niagara"),
    (r"\b(html tag delimiter|html operator)\b", "niagara"),

    # Attribute names.
    (r"\b(xaml|xml|axml)\s+attribute\b", "quartz"),
    (r"\b(xmlattributenameclassificationformat|xml attribute name classification format)\b", "quartz"),
    (r"\b(xml doc attribute|xml doc attribute classification format|xmldocattributeclassificationformat)\b", "quartz"),
    (r"\b(xml literal|xml doc comment|axml)\s*-\s*attribute name\b", "quartz"),
    (r"\b(html attribute|html attribute name|markup attribute|razor component attribute|razor tag helper attribute|razor directive attribute)\b", "quartz"),

    # Normal quoted attribute values.
    (r"\b(xaml|xml|axml)\s+attribute quotes\b", "green"),
    (r"\b(xaml|xml|axml)\s+attribute value\b", "green"),
    (r"\b(xmlattributequotesclassificationformat|xml attribute quotes classification format)\b", "green"),
    (r"\b(xmlattributevalueclassificationformat|xml attribute value classification format)\b", "green"),
    (r"\b(xml literal|xml doc comment|axml)\s*-\s*attribute quotes\b", "green"),
    (r"\b(xml literal|xml doc comment|axml)\s*-\s*attribute value\b", "green"),
    (r"\b(html attribute value|markup attribute value)\b", "green"),

    # XAML markup extensions, e.g. {Binding Left.Name, UpdateSourceTrigger=PropertyChanged}
    (r"\bxaml markup extension class\b", "yellow"),
    (r"\bxaml markup extension parameter name\b", "fg+1"),
    (r"\bxaml markup extension parameter value\b", "quartz"),

    # If VS exposes binding/path-like things under other names, keep them white.
    (r"\b(binding path|markup extension path|path expression|property path|attached property)\b", "fg+1"),
    (r"\b(markup extension name|markup extension identifier|binding identifier)\b", "fg+1"),

    # Markup extension punctuation: { } , = .
    (r"\b(markup extension delimiter|markup extension punctuation|binding delimiter|binding punctuation)\b", "niagara"),

    # Comments / CDATA / processing instructions.
    (r"\b(xaml|xml|axml)\s+comment\b", "brown"),
    (r"\b(xmlcommentclassificationformat|xml comment classification format)\b", "brown"),
    (r"\b(xml doc comment|xmldoccommentclassificationformat|xml doc comment classification format)\b", "brown"),
    (r"\b(xml literal|xml doc comment|axml)\s*-\s*comment\b", "brown"),

    (r"\b(xaml|xml|axml)\s+cdata section\b", "green"),
    (r"\b(xmlcdatasectionclassificationformat|xml cdata section classification format)\b", "green"),
    (r"\b(xml literal|xml doc comment|axml)\s*-\s*cdata section\b", "green"),

    (r"\b(xaml|xml|axml)\s+processing instruction\b", "quartz"),
    (r"\b(xmlprocessinginstructionclassificationformat|xml processing instruction classification format)\b", "quartz"),
    (r"\b(xml literal|xml doc comment|axml)\s*-\s*processing instruction\b", "quartz"),

    # Text/entity content.
    (r"\b(html entity|entity reference|xml literal\s*-\s*entity reference|xml doc comment\s*-\s*entity reference|axml\s*-\s*entity reference)\b", "niagara"),
    (r"\b(xmltextclassificationformat|xml text classification format|xaml text|xml text|axml\s*-\s*text|xml literal\s*-\s*text|xml doc comment\s*-\s*text)\b", "fg"),
    
    # Variables / values / punctuation.
    # These must stay after the XML / XAML / markup-specific rules.

    # Links / namespace-ish identifiers.
    (r"\b(namespace|selector|entity|url|link|hyperlink)\b", "niagara"),

    # Generic markup names. XAML/XML-specific names should already have matched above.
    (r"\b(tag helper|element name|xml name|html element|markup node)\b", "yellow"),

    # Attribute values / quotes.
    (r"\b(attribute quotes|quotes)\b", "green"),
    (r"\b(attribute value|property value|parameter value)\b", "green"),

    # Ordinary values.
    (r"\b(value)\b", "fg+1"),

    # Ordinary identifiers.
    (r"\b(attribute|property name|property|field|variable|parameter|local|identifier|name)\b", "fg+1"),

    # Operators can stay accented; structural punctuation should be quiet.
    (r"\b(operator|alternation|quantifier|anchor)\b", "niagara"),
    (r"\b(delimiter|punctuation|brace|bracket)\b", "fg"),

    # Muted / disabled / adornment text.
    (r"\b(excluded|unnecessary|disabled|inactive|unavailable|dimmed|watermark|hint|placeholder)\b", "niagara-1"),
    (r"\b(glyph|icon|chevron|arrow|bullet|marker|scroll buttons?)\b", "niagara"),
    (r"\b(header|title|caption|heading)\b", "fg+1"),

    # Explicit boring UI foregrounds. These intentionally render as normal fg,
    # but prevent the audit from treating them as accidental fallthrough.
    (r"\b(button|checkbox|checkmark|dropdown|wonderbar|pivotbar)\b", "fg"),
    (r"\b(listitem|list item|resultlistitem|tabitem|tab item|categorytab|category tab)\b", "fg"),
    (r"\b(form|grid|cell|groupbox|htmlcontrol|readonlycontrol|activecontrol|defaultcontrol)\b", "fg"),
    (r"\b(description|details|duration|timestamp|body|h1|numbered list item)\b", "fg"),
    (r"\b(content|text|foreground)\b", "fg"),
]

# Ordered background roles. Earlier patterns win.
BACKGROUND_PATTERNS: list[tuple[str, str]] = [
    # State / diagnostics first: these must win over literal colour words.
    (r"\b(error|invalid|failed|failure|critical|conflict)\b", "red"),
    (r"\b(warning|caution|alert)\b", "brown"),
    (r"\b(add|adds|addition|additions|added|accepted|success|resolved)\b", "green"),
    (r"\b(deleted|removed|remove|deletion)\b", "red-1"),
    (r"\b(changed|modified|modification|track reverted)\b", "bg+3"),

    # Debug / execution state.
    (r"\bbreakpoint\b", "red"),
    (r"\b(tracepoint|logpoint|snappoint)\b", "wisteria"),
    (r"\b(current statement|currentstatement|debuglocation|active statement|executing thread|instruction pointer|current)\b", "niagara-2"),

    # Interaction state.
    (r"\b(selected|selection|selectedtext|selected line|highlighted reference|highlighted text|matched selected)\b", "bg+3"),
    (r"\b(pressed|mousedown|mouse down|checked)\b", "niagara"),
    (r"\b(disabled|inactive|unavailable|dimmed)\b", "bg+1"),
    (r"\b(hover|mouseover|mouse over|focused|focus|active)\b", "bg+1"),

    # Structural UI surfaces.
    (r"\bshadow\b", "bg-1"),
    (r"\b(border|separator|outline|divider|splitter|gridline|rule|underline)\b", "bg+1"),
    (r"\b(scrollbar|thumb|overview margin|scroll bar)\b", "bg+2"),
    (r"\b(tab background|tabitem|tab)\b", "bg+1"),
    (r"\b(menu|toolbar|commandbar|statusbar|command shelf|shelf)\b", "bg"),
    (r"\b(input|combobox|combo|list item|listitem|button|toggle|control|card)\b", "bg+1"),
    (r"\b(dialog|tool window|toolwindow|panel|pane|window|floating menu|popup|tooltip)\b", "bg"),
    (r"\b(text editor|plain text|editor|document|surface|canvas|artboard|designer|grid|tree|background|fill)\b", "bg"),

    # Named decorative palette ramps last.
    (r"\b(dark red|red)\b", "red"),
    (r"\b(orange|brown)\b", "brown"),
    (r"\byellow\b", "yellow"),
    (r"\b(green|teal)\b", "green"),
    (r"\b(light blue|dark blue|blue)\b", "niagara"),
    (r"\b(grape|purple|lavender|magenta|pink)\b", "wisteria"),
    (r"\b(grey|gray|neutral)\b", "bg+3"),
    (r"\bprimary alt\b", "niagara"),
    (r"\bprimary\b", "niagara"),
    (r"\bsecondary\b", "bg+3"),
    (r"\b(tertiary|quaternary|quinary|senary)\b", "bg+2"),
]

FOREGROUND_CONCEPT = re.compile(
    r"text|foreground|caption|glyph|icon|chevron|arrow|bullet|marker|link|hyperlink|"
    r"identifier|keyword|comment|string|literal|number|numeric|operator|preprocessor|macro|"
    r"namespace|function|method|event|type|class|struct|enum|interface|delegate|record|"
    r"variable|parameter|field|property|attribute|delimiter|punctuation|brace|bracket|"
    r"element|selector|tag|name\b|value|label|caret",
    re.IGNORECASE,
)

BACKGROUND_CONCEPT = re.compile(
    r"background|surface|fill|canvas|panel|pane|window|shelf|margin|selection|selected|"
    r"highlight|tab|menu|toolbar|commandbar|statusbar|scrollbar|thumb|border|separator|"
    r"outline|divider|splitter|gridline|shadow|button|input|combo|listitem|dialog",
    re.IGNORECASE,
)

def normalise(text: str) -> str:
    # Split separators and Camel/PascalCase Visual Studio token names so
    # CppFunctionSemanticTokenFormat can match "function", etc.
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", text)
    return re.sub(r"[_.\-/]+", " ", text).lower()

def pattern_role(
    patterns: list[tuple[str, str]],
    category: str,
    name: str,
    *,
    include_category: bool,
) -> str | None:
    haystack = normalise(f"{category} {name}" if include_category else name)
    for pattern, role in patterns:
        if re.search(pattern, haystack, re.IGNORECASE):
            return role
    return None

def exact_roles(category: str, name: str) -> tuple[str | None, str | None] | None:
    return EXACT.get((category, name)) or EXACT.get((None, name)) or NAME_EXACT.get(name)

def foreground_role(category: str, name: str, source: str | None) -> str:
    exact = exact_roles(category, name)
    if exact and exact[0]:
        return exact[0]

    role = pattern_role(FOREGROUND_PATTERNS, category, name, include_category=False)
    if role:
        return role

    _, rgb = split_argb(source)
    direct = PALETTE_BY_RGB.get(rgb.upper())
    # Do not preserve raw black as a foreground; most VS black text was
    # black-on-light in the source theme and becomes unreadable in Gruber.
    if direct and direct != "black":
        return direct

    return source_colour_role(source, foreground=True)

def background_role(category: str, name: str, source: str | None) -> str:
    exact = exact_roles(category, name)
    if exact and exact[1]:
        return exact[1]

    role = pattern_role(BACKGROUND_PATTERNS, category, name, include_category=True)
    if role:
        return role

    _, rgb = split_argb(source)
    direct = PALETTE_BY_RGB.get(rgb.upper())
    # Do not preserve raw black as a fill. Gruber's dark base is bg/bg-1,
    # not literal #000000.
    if direct and direct != "black":
        return direct

    return source_colour_role(source, foreground=False)

def source_colour_role(source: str | None, foreground: bool) -> str:
    """Map an arbitrary VS/Dark-theme source colour to a gruber role."""
    _, rgb = split_argb(source)
    r = int(rgb[0:2], 16)
    g = int(rgb[2:4], 16)
    b = int(rgb[4:6], 16)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b

    maxc = max(r, g, b)
    minc = min(r, g, b)
    chroma = maxc - minc

    if chroma > 35:
        if r > g + 35 and r > b + 35:
            # Orange/brown UI accents are comments/warnings unless clearly red.
            if g > 95 and b < 120:
                return "brown"
            return "red+1" if foreground else "red"
        if g > r + 25 and g > b + 25:
            return "green"
        if b > r + 25 and b > g + 10:
            if r > 90:
                return "wisteria"
            return "niagara"
        if r > 140 and b > 140:
            return "wisteria"
        if r > 160 and g > 135 and b < 120:
            return "yellow"

    if foreground:
        if lum >= 220:
            return "fg+2"
        if lum >= 185:
            return "fg+1"
        if lum >= 130:
            return "quartz"
        if lum >= 75:
            return "niagara-1"
        return "fg"

    if lum < 24:
        return "bg-1"
    if lum < 38:
        return "bg"
    if lum < 58:
        return "bg+1"
    if lum < 82:
        return "bg+2"
    if lum < 115:
        return "bg+3"
    return "bg+4"

def is_foreground_concept(category: str, name: str) -> bool:
    # Use the token name only. Including category makes every Text Editor token
    # look foreground-like and corrupts real background slots.
    return bool(FOREGROUND_CONCEPT.search(normalise(name)))

def is_background_concept(category: str, name: str) -> bool:
    return bool(BACKGROUND_CONCEPT.search(normalise(f"{category} {name}")))

def slot_is_valid(slot: dict[str, Any] | None) -> bool:
    return bool(slot and slot.get("valid") and slot.get("type") != "CT_INVALID")

def should_treat_background_as_foreground(
    category: str,
    name: str,
    background: dict[str, Any] | None,
    foreground: dict[str, Any] | None,
) -> bool:
    """VS often stores glyph/text/link colours in the Background element."""
    if not slot_is_valid(background):
        return False
    if slot_is_valid(foreground):
        return False
    if not is_foreground_concept(category, name):
        return False

    # Avoid names where a foreground-ish word appears inside a real fill token.
    if re.search(r"background|border|selected|selection|highlight|hover|pressed|mousedown|mouseover", name, re.IGNORECASE):
        return False

    return True

def resolve_slot(
    category: str,
    name: str,
    slot_name: str,
    slot: dict[str, Any] | None,
    other_slot: dict[str, Any] | None,
) -> SlotResult | None:
    if slot is None:
        return None

    slot_type = slot.get("type") or "CT_INVALID"
    source = (slot.get("source") or "00000000").upper()

    if not slot.get("valid") or slot_type == "CT_INVALID":
        return SlotResult("CT_INVALID", "00000000")

    # Non-raw slots are inheritance/system references rather than literal RGB.
    # Preserving them avoids turning CT_AUTOMATIC/00000000 into black.
    if slot_type != "CT_RAW":
        return SlotResult(slot_type, source)

    alpha, rgb = split_argb(source)
    if alpha == "00":
        return SlotResult("CT_RAW", source)

    exact_role = SLOT_EXACT.get((category, name, slot_name))
    if exact_role:
        return SlotResult("CT_RAW", preserve_alpha(source, exact_role))

    if slot_name == "Foreground":
        role = foreground_role(category, name, source)
        return SlotResult("CT_RAW", preserve_alpha(source, role))

    if should_treat_background_as_foreground(category, name, slot, other_slot):
        role = foreground_role(category, name, source)
    else:
        role = background_role(category, name, source)

    return SlotResult("CT_RAW", preserve_alpha(source, role))

def emit_slot(lines: list[str], slot_name: str, result: SlotResult | None) -> None:
    if result is None:
        return
    lines.append(f'        <{slot_name} Type="{result.type}" Source="{result.source}" />')

def main() -> None:
    with open(TOKENS_PATH, encoding="utf-8") as f:
        categories = json.load(f)

    lines: list[str] = []
    lines.append("<Themes>")
    lines.append(
        f'  <Theme Name="{escape(THEME_NAME)}" GUID="{THEME_GUID}" BaseGUID="{BASE_GUID}">'
    )

    total_colors = 0
    for cat in categories:
        cat_name = cat["name"]
        cat_guid = cat["guid"]
        lines.append(f'    <Category Name="{escape(cat_name)}" GUID="{cat_guid}">')

        for color in cat["colors"]:
            total_colors += 1
            name = color["name"]
            background = color.get("background")
            foreground = color.get("foreground")

            bg = resolve_slot(cat_name, name, "Background", background, foreground)
            fg = resolve_slot(cat_name, name, "Foreground", foreground, background)

            lines.append(f'      <Color Name="{escape(name)}">')
            emit_slot(lines, "Background", bg)
            emit_slot(lines, "Foreground", fg)
            lines.append("      </Color>")

        lines.append("    </Category>")

    lines.append("  </Theme>")
    lines.append("</Themes>")

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print(f"wrote {OUTPUT_PATH}: {len(categories)} categories, {total_colors} colors")

if __name__ == "__main__":
    main()
