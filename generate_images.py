#!/usr/bin/python3

import asyncio
import os
import textwrap
from datetime import date, datetime, timezone
from html import escape
from typing import Dict, List, Optional, Tuple

import aiohttp

from github_stats import Queries, Stats


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


PIN_CARD_WIDTH = 460
PIN_CARD_HEIGHT = 118
PIN_GAP = 16
PIN_DESC_CHARS = 58


def time_ago(timestamp: str) -> str:
    """
    Format an ISO 8601 timestamp as a short relative age (e.g., "3d ago")
    :param timestamp: GitHub API timestamp such as 2026-10-27T03:56:20Z
    """
    pushed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    days = (datetime.now(timezone.utc) - pushed).days
    if days < 1:
        return "today"
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def wrap_description(description: Optional[str]) -> List[str]:
    """
    Wrap a repository description to at most two lines, with an ellipsis
    :param description: repository description, possibly empty
    """
    if not description:
        return ["// no description"]
    lines = textwrap.wrap(description, PIN_DESC_CHARS)
    if len(lines) > 2:
        lines = lines[:2]
        lines[1] = lines[1][: PIN_DESC_CHARS - 1].rstrip() + "…"
    return lines


async def generate_pinned(s: Stats, login: str) -> None:
    """
    Generate a terminal-style SVG grid of the repositories pinned on the profile
    :param s: Represents user's GitHub statistics
    :param login: GitHub username shown in the prompt
    """
    with open("templates/pinned.svg", "r") as f:
        output = f.read()

    repos = (
        (await s.queries.query(Queries.pinned_repos()))
        .get("data", {})
        .get("viewer", {})
        .get("pinnedItems", {})
        .get("nodes", [])
    )

    cards = ""
    for i, repo in enumerate(repos):
        x = 22 + (i % 2) * (PIN_CARD_WIDTH + PIN_GAP)
        y = 74 + (i // 2) * (PIN_CARD_HEIGHT + PIN_GAP)
        tags = []
        if repo.get("isPrivate"):
            tags.append("private")
        if repo.get("isArchived"):
            tags.append("archived")
        tag = f"[{', '.join(tags) or 'public'}]"
        language = (repo.get("primaryLanguage") or {}).get("name", "—")
        desc = "".join(
            f'<text class="desc" x="{x + 16}" y="{y + 52 + j * 18}">'
            f"{escape(line)}</text>"
            for j, line in enumerate(wrap_description(repo.get("description")))
        )
        cards += f"""
<g class="line" style="animation-delay: {(i + 1) * ROW_DELAY_MS}ms">
<rect class="card" x="{x}" y="{y}" width="{PIN_CARD_WIDTH}" height="{PIN_CARD_HEIGHT}" rx="6" />
<text class="name" x="{x + 16}" y="{y + 28}">▸ {escape(repo.get("name", ""))}</text>
<text class="tag" x="{x + PIN_CARD_WIDTH - 16}" y="{y + 27}" text-anchor="end">{tag}</text>
{desc}
<text class="meta" x="{x + 16}" y="{y + PIN_CARD_HEIGHT - 16}"><tspan>● {escape(language)}</tspan><tspan class="dim">   ★ </tspan><tspan>{repo.get("stargazerCount", 0):,}</tspan><tspan class="dim">   ⑂ </tspan><tspan>{repo.get("forkCount", 0):,}</tspan><tspan class="dim">   ↻ </tspan><tspan>{time_ago(repo["pushedAt"]) if repo.get("pushedAt") else "—"}</tspan></text>
</g>
"""

    if not repos:
        cards = (
            '<text x="22" y="86" class="line" style="animation-delay: 120ms">'
            '<tspan class="dim">no pinned repositories</tspan></text>\n'
        )

    rows = max(1, (len(repos) + 1) // 2)
    height = 74 + rows * (PIN_CARD_HEIGHT + PIN_GAP) - PIN_GAP + 22
    output = render(
        output,
        {
            "login": escape(login),
            "cards": cards,
            "height": str(height),
            "inner_height": str(height - 2),
            "border_height": str(height - 1),
        },
    )

    generate_output_folder()
    with open("generated/pinned.svg", "w") as f:
        f.write(output)


HEATMAP_X = 52
HEATMAP_Y = 82
HEATMAP_STEP = 14
HEATMAP_CELL = 11
CONTRIB_LEVELS = {
    "NONE": "l0",
    "FIRST_QUARTILE": "l1",
    "SECOND_QUARTILE": "l2",
    "THIRD_QUARTILE": "l3",
    "FOURTH_QUARTILE": "l4",
}


def streaks(days: List[Dict]) -> Tuple[int, int]:
    """
    Compute the current and longest streaks of days with contributions
    :param days: contribution days in chronological order
    :return: (current streak, longest streak) in days
    """
    longest = run = 0
    for day in days:
        run = run + 1 if day.get("contributionCount", 0) > 0 else 0
        longest = max(longest, run)

    current = 0
    # Today without contributions yet should not break the streak
    trailing = days[:-1] if days and days[-1].get("contributionCount", 0) == 0 else days
    for day in reversed(trailing):
        if day.get("contributionCount", 0) == 0:
            break
        current += 1
    return current, longest


async def generate_contributions(s: Stats, login: str) -> None:
    """
    Generate a Matrix-green heatmap of the past year of contributions
    :param s: Represents user's GitHub statistics
    :param login: GitHub username shown in the prompt
    """
    with open("templates/contributions.svg", "r") as f:
        output = f.read()

    calendar = (
        (await s.queries.query(Queries.contrib_calendar()))
        .get("data", {})
        .get("viewer", {})
        .get("contributionsCollection", {})
        .get("contributionCalendar", {})
    )
    weeks = calendar.get("weeks", [])
    days = [day for week in weeks for day in week.get("contributionDays", [])]

    grid = ""
    month_starts: List[Tuple[int, str]] = []
    last_month = None
    for w, week in enumerate(weeks):
        x = HEATMAP_X + w * HEATMAP_STEP
        cells = ""
        for day in week.get("contributionDays", []):
            weekday = (date.fromisoformat(day["date"]).weekday() + 1) % 7
            level = CONTRIB_LEVELS.get(day.get("contributionLevel"), "l0")
            today = " today" if day is days[-1] else ""
            cells += (
                f'<rect class="{level}{today}" x="{x}" '
                f'y="{HEATMAP_Y + weekday * HEATMAP_STEP}" width="{HEATMAP_CELL}" '
                f'height="{HEATMAP_CELL}" rx="2"><title>{day["date"]}: '
                f'{day.get("contributionCount", 0)}</title></rect>'
            )
        grid += f'<g class="col" style="animation-delay: {w * 15}ms">{cells}</g>\n'

        first = week.get("contributionDays", [{}])[0].get("date")
        if first and first[:7] != last_month:
            month_starts.append((x, date.fromisoformat(first).strftime("%b")))
            last_month = first[:7]

    # Drop the leading partial month if its label would overlap the next one
    if len(month_starts) > 1 and month_starts[1][0] - month_starts[0][0] < 3 * HEATMAP_STEP:
        month_starts = month_starts[1:]
    months = "".join(
        f'<text class="axis" x="{x}" y="{HEATMAP_Y - 6}">{label}</text>\n'
        for x, label in month_starts
    )

    current, longest = streaks(days)
    best = max(days, key=lambda d: d.get("contributionCount", 0), default=None)
    best_text = (
        f'{best["contributionCount"]} · '
        f'{date.fromisoformat(best["date"]).strftime("%b %d")}'
        if best and best.get("contributionCount", 0) > 0
        else "—"
    )
    summary_items = [
        ("total_1y", f'{calendar.get("totalContributions", 0):,}'),
        ("current_streak", f"{current}d"),
        ("longest_streak", f"{longest}d"),
        ("best_day", best_text),
    ]
    summary = ""
    for i, (key, value) in enumerate(summary_items):
        y = 88 + i * 32
        summary += (
            f'<g class="line" style="animation-delay: {900 + i * ROW_DELAY_MS}ms">'
            f'<text class="key" x="832" y="{y}">{key}</text>'
            f'<text class="val" x="832" y="{y + 17}">{escape(value)}</text></g>\n'
        )

    output = render(
        output,
        {
            "login": escape(login),
            "grid": grid,
            "months": months,
            "summary": summary,
            "mon_y": str(HEATMAP_Y + 1 * HEATMAP_STEP + 9),
            "wed_y": str(HEATMAP_Y + 3 * HEATMAP_STEP + 9),
            "fri_y": str(HEATMAP_Y + 5 * HEATMAP_STEP + 9),
        },
    )

    generate_output_folder()
    with open("generated/contributions.svg", "w") as f:
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
            generate_languages(s, user),
            generate_overview(s, user),
            generate_pinned(s, user),
            generate_contributions(s, user),
        )


if __name__ == "__main__":
    asyncio.run(main())
