import re
import requests
import markdown
import pandas as pd
from io import StringIO
from pathlib import Path
from bs4 import BeautifulSoup
from markdown_it import MarkdownIt
from utils.logging_config import get_logger

logger = get_logger(__name__)


def load_html(source):
    if Path(source).is_file():
        with open(source, "r", encoding="utf-8") as f:
            return f.read()
    response = requests.get(source)
    response.raise_for_status()
    return response.text


def parse_html(source):
    html = load_html(source)
    soup = BeautifulSoup(html, "html.parser")

    return soup


def parse_tables(soup) -> list[pd.DataFrame]:
    tables = soup.find_all("table")
    dataframes = []

    for i, table in enumerate(tables, start=1):
        try:
            table_html = StringIO(str(table))
            df = pd.read_html(table_html)[0]
            dataframes.append(df)
        except Exception as e:
            logger.error(f"Skipping table {i} due to error: {e}")

    return dataframes


def parse_markdown(md):
    md = MarkdownIt()
    tokens = md.parse(md)
    result = []
    for token in tokens:
        result.append((token.type, token.tag, token.content))

    return result


def is_valid_markdown(md_text):
    try:
        html = markdown.markdown(md_text)
        return True, html
    except Exception as e:
        return False, str(e)


def clean_md_text(text):
    # Replace escaped characters with spaces
    text = (
        text.replace("\\r\\n", " ")
        .replace("\\n", " ")
        .replace("\\r", " ")
        .replace("\u2026", "...")
        .replace("\u00a0", " ")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2022", "*")
    )

    # Remove URLs (http, https, www)
    text = re.sub(r"(https?://\S+|www\.\S+)", "", text)

    # Remove Jira/Confluence markup
    text = re.sub(r"\{color[^}]*\}.*?\{color\}", "", text)  # Remove color markup
    text = re.sub(r"\{\*\}(.*?)\{\*\}", r"\1", text)  # Convert {*}text{*} to text
    text = re.sub(r"\{\{([^}]*)\}\}", r"\1", text)  # Convert {{text}} to text
    text = re.sub(r"\[([^|]*)\|[^\]]*\]", r"\1", text)  # Convert [text|url] to text
    text = re.sub(r"_{color:[^}]*}[^{]*{color}_", "", text)  # Remove color formatting

    # Remove Confluence-style headers like h1. or h2.
    text = re.sub(r"\bh[1-6]\.\s*", "", text)

    # Remove table markup
    text = re.sub(r"\|[^|]*\|", "", text)  # Remove table cells
    text = re.sub(r"^\s*\|.*\|\s*$", "", text, flags=re.MULTILINE)  # Remove table rows

    # Remove bullet characters, markdown-style emphasis, or stray symbols
    text = re.sub(r"[*#<>\[\]]+", "", text)

    # Remove placeholder links or mentions like <link to ...>
    text = re.sub(r"<link[^>]*>", "", text)

    # Remove extra colons (e.g. "Open questions::")
    text = re.sub(r"::+", ":", text)

    # Collapse multiple spaces and strip
    text = re.sub(r"\s+", " ", text).strip()

    return text


def convert_json_to_markdown(data: dict) -> str:
    """
    Convert feature gate correlation data to readable Markdown.

    Args:
        data: Dictionary mapping feature gates to related work items

    Returns:
        Formatted Markdown string with hierarchical organization
    """

    def format_description(text):
        # Convert wiki-style formatting to markdown
        text = re.sub(r"\{\{(.*?)\}\}", r"`\1`", text)  # {{feature}} → `feature`
        text = re.sub(r"\*(.*?)\*", r"**\1**", text)  # *bold* → **bold**
        text = re.sub(
            r"\[([^\|]+)\|([^\]]+)\]", r"[\1](\2)", text
        )  # [text|url] → [text](url)
        return text.strip()

    lines = []
    for feature_gate, issues in data.items():
        lines.append(f"## {feature_gate}\n")
        for idx, issue in enumerate(issues, 1):
            lines.append(f"### {idx}. {issue.get('summary', 'No summary')}\n")

            # Show epic relationships for context
            if "epic_key" in issue:
                lines.append(f"**Epic**: `{issue['epic_key']}`\n")

            # Include formatted descriptions
            if "description" in issue:
                lines.append(
                    f"**Description:**\n\n{format_description(issue['description'])}\n"
                )

            # Show related GitHub items
            for src, entries in issue.items():
                if src == "GITHUB":
                    lines.append(f"**GitHub Items:**\n")
                    for entry in entries:
                        lines.append(
                            f"- **[{entry.get('title')}]** (ID: {entry.get('id')})\n"
                        )
                        if entry.get("body"):
                            lines.append(f"  - {entry['body'].strip()}\n")
        lines.append("\n---\n")  # Feature gate separator

    return "\n".join(lines)
