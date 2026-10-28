#!/usr/bin/python3

import asyncio
import os
from html import escape
from typing import Dict

import aiohttp

from github_stats import Stats


################################################################################
# Helper Functions
################################################################################


def generate_output_folder() -> None:
    """
    Create the output folder if it does not already exist
    """
    if not os.path.isdir("generated"):
        os.mkdir("generated")


################################################################################
# Individual Image Generation Functions
################################################################################

FIRST_ROW_Y = 78
ROW_HEIGHT = 21
ROW_DELAY_MS = 120
MAX_LANGUAGES = 6
BAR_WIDTH = 24


def render(template: str, values: Dict[str, str]) -> str:
    """
    Substitute {{ key }} placeholders in a template without regex escaping issues
    :param template: SVG template contents
    :param values: mapping from placeholder name to replacement text
    :return: rendered SVG
    """
    for key, value in values.items():
        template = template.replace(f"{{{{ {key} }}}}", value)
    return template


def cursor_values(num_rows: int) -> Dict[str, str]:
    """
    Position the blinking prompt below the last row and reveal it after the rows
    :param num_rows: number of rows printed between the command and the cursor
    """
    return {
        "cursor_y": str(FIRST_ROW_Y + num_rows * ROW_HEIGHT + 3),
        "cursor_delay": str((num_rows + 1) * ROW_DELAY_MS),
    }


async def generate_overview(s: Stats, login: str) -> None:
    """
    Generate a terminal-style SVG card with summary statistics
    :param s: Represents user's GitHub statistics
    :param login: GitHub username shown in the prompt
    """
    with open("templates/overview.svg", "r") as f:
        output = f.read()

    added, deleted = await s.lines_changed
    stats = [
        ("stars", f"{await s.stargazers:,}"),
        ("forks", f"{await s.forks:,}"),
        ("contributions", f"{await s.total_contributions:,}"),
        ("lines_changed", f"+{added:,} / -{deleted:,}"),
        ("views_14d", f"{await s.views:,}"),
        ("repos_contributed", f"{len(await s.repos):,}"),
    ]

    rows = ""
    for i, (key, value) in enumerate(stats):
        dots = "." * (22 - len(key))
        rows += (
            f'<text x="30" y="{FIRST_ROW_Y + i * ROW_HEIGHT}" class="line" '
            f'style="animation-delay: {(i + 1) * ROW_DELAY_MS}ms">'
            f'<tspan class="key">{key}</tspan><tspan class="dots"> {dots} </tspan>'
            f'<tspan class="val">{escape(value)}</tspan></text>\n'
        )

    output = render(
        output,
        {"login": escape(login), "rows": rows, **cursor_values(len(stats))},
    )

    generate_output_folder()
    with open("generated/overview.svg", "w") as f:
        f.write(output)


async def generate_languages(s: Stats, login: str) -> None:
    """
    Generate a terminal-style SVG card with ASCII bars of the languages used
    :param s: Represents user's GitHub statistics
    :param login: GitHub username shown in the prompt
    """
    with open("templates/languages.svg", "r") as f:
        output = f.read()

    sorted_languages = sorted(
        (await s.languages).items(), reverse=True, key=lambda t: t[1].get("size")
    )[:MAX_LANGUAGES]

    rows = ""
    for i, (lang, data) in enumerate(sorted_languages):
        prop = data.get("prop", 0)
        filled = max(1, round(prop / 100 * BAR_WIDTH)) if prop > 0 else 0
        name = lang if len(lang) <= 12 else lang[:11] + "…"
        rows += (
            f'<text x="30" y="{FIRST_ROW_Y + i * ROW_HEIGHT}" class="line" '
            f'style="animation-delay: {(i + 1) * ROW_DELAY_MS}ms">'
            f'<tspan class="lang">{escape(name):<12}</tspan> '
            f'<tspan class="bar">{"█" * filled}</tspan>'
            f'<tspan class="track">{"░" * (BAR_WIDTH - filled)}</tspan> '
            f'<tspan class="pct">{prop:6.2f}%</tspan></text>\n'
        )

    output = render(
        output,
        {
            "login": escape(login),
            "count": str(len(sorted_languages)),
            "rows": rows,
            **cursor_values(len(sorted_languages)),
        },
    )

    generate_output_folder()
    with open("generated/languages.svg", "w") as f:
        f.write(output)


################################################################################
# Main Function
################################################################################


async def main() -> None:
    """
    Generate all badges
    """
    access_token = os.getenv("ACCESS_TOKEN")
    if not access_token:
        # access_token = os.getenv("GITHUB_TOKEN")
        raise Exception("A personal access token is required to proceed!")
    user = os.getenv("GITHUB_ACTOR")
    if user is None:
        raise RuntimeError("Environment variable GITHUB_ACTOR must be set.")
    exclude_repos = os.getenv("EXCLUDED")
    excluded_repos = (
        {x.strip() for x in exclude_repos.split(",")} if exclude_repos else None
    )
    exclude_langs = os.getenv("EXCLUDED_LANGS")
    excluded_langs = (
        {x.strip() for x in exclude_langs.split(",")} if exclude_langs else None
    )
    # Convert a truthy value to a Boolean
    raw_ignore_forked_repos = os.getenv("EXCLUDE_FORKED_REPOS")
    ignore_forked_repos = (
        not not raw_ignore_forked_repos
        and raw_ignore_forked_repos.strip().lower() != "false"
    )
    async with aiohttp.ClientSession() as session:
        s = Stats(
            user,
            access_token,
            session,
            exclude_repos=excluded_repos,
            exclude_langs=excluded_langs,
            ignore_forked_repos=ignore_forked_repos,
        )
        # get_stats() resets its fields before fetching, so populate them once
        # up front instead of letting both cards race to read partial results
        await s.get_stats()
        await asyncio.gather(
            generate_languages(s, user), generate_overview(s, user)
        )


if __name__ == "__main__":
    asyncio.run(main())
