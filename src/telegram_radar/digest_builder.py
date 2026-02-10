from datetime import datetime, timedelta, timezone

from telegram_radar.models import DigestBatchResult, DigestItem


class DigestBuilder:
    def build_digest(
        self,
        batch_results: list[DigestBatchResult],
        max_items: int,
        urgent_days: int,
    ) -> str:
        all_items: list[DigestItem] = []
        for br in batch_results:
            all_items.extend(br.items)

        if not all_items:
            return "No new posts found in Radar channels since last check."

        now = datetime.now(timezone.utc).date()
        cutoff = now + timedelta(days=urgent_days)

        urgent: list[DigestItem] = []
        other: list[DigestItem] = []

        for item in all_items:
            if item.deadline:
                try:
                    dl = datetime.strptime(item.deadline, "%Y-%m-%d").date()
                    if dl <= cutoff:
                        urgent.append(item)
                        continue
                except ValueError:
                    pass
            other.append(item)

        urgent.sort(key=lambda x: x.deadline or "9999-99-99")
        other.sort(key=lambda x: x.priority, reverse=True)

        ordered = urgent + other
        shown = ordered[:max_items]
        remaining = len(ordered) - len(shown)

        today_str = now.isoformat()
        lines: list[str] = [f"\U0001f4cb Digest \u2014 {today_str}"]

        if urgent:
            lines.append("")
            lines.append(
                f"\U0001f534 Urgent (deadline within {urgent_days} days):"
            )
            for item in shown:
                if item not in urgent:
                    break
                lines.append(_format_item(item))
            # Switch to other
            other_shown = [i for i in shown if i not in urgent]
            if other_shown:
                lines.append("")
                lines.append("\U0001f4cc Other highlights:")
                for item in other_shown:
                    lines.append(_format_item(item))
        else:
            lines.append("")
            lines.append("\U0001f4cc Highlights:")
            for item in shown:
                lines.append(_format_item(item))

        if remaining > 0:
            lines.append("")
            lines.append(f"...and {remaining} more items")

        return "\n".join(lines)


def _format_item(item: DigestItem) -> str:
    parts: list[str] = [
        f"\u2022 **{item.title}** \u2014 {item.why_relevant}"
    ]
    if item.deadline or item.action:
        detail_parts: list[str] = []
        if item.deadline:
            detail_parts.append(f"\U0001f4c5 Deadline: {item.deadline}")
        if item.action:
            detail_parts.append(f"Action: {item.action}")
        parts.append(f"  {' | '.join(detail_parts)}")

    parts.append(f'  \U0001f4ac "{item.post_quote}"')
    if item.comment_quote:
        parts.append(f'  \U0001f4ac Comment: "{item.comment_quote}"')
    parts.append(f"  \U0001f517 [Source]({item.source_url})")
    return "\n".join(parts)
