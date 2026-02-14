"""
Analytics API Routes
Provides aggregated analytics data for the dashboard
"""

import contextlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import TypedDict

from fastapi import APIRouter, Query

from core.config import get_screenshots_dir
from core.database import db


class HeatmapCell(TypedDict):
    date: str
    day_of_week: int
    day_label: str
    hour: int
    count: int
    screenshot_ids: list[int]


class DailyDataPoint(TypedDict):
    date: str
    count: int
    moving_avg: float


router = APIRouter(prefix="/analytics", tags=["Analytics"])


def parse_timestamp(ts: str) -> datetime:
    """Convert YYMMDDHHMMSS to datetime."""
    if len(ts) != 12:
        return datetime.now()
    year = 2000 + int(ts[0:2])
    month = int(ts[2:4])
    day = int(ts[4:6])
    hour = int(ts[6:8])
    minute = int(ts[8:10])
    second = int(ts[10:12])
    return datetime(year, month, day, hour, minute, second)


def format_timestamp(dt: datetime) -> str:
    """Convert datetime back to YYMMDDHHMMSS format."""
    return dt.strftime("%y%m%d%H%M%S")


@router.get("/overview")
async def get_overview():
    """
    Get overview statistics for the analytics dashboard.

    Returns high-level metrics about screenshots, storage, and processing status.
    """
    with db.cursor() as cur:
        # Total screenshots
        cur.execute("SELECT COUNT(*) FROM screenshots")
        total_screenshots = cur.fetchone()[0]

        # OCR processed count
        cur.execute("SELECT COUNT(*) FROM screenshots WHERE has_ocr = 1")
        ocr_processed_count = cur.fetchone()[0]

        # Compressed count
        cur.execute("SELECT COUNT(*) FROM screenshots WHERE is_compressed = 1")
        compressed_count = cur.fetchone()[0]

        # Screenshots today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_ts = format_timestamp(today_start)
        cur.execute("SELECT COUNT(*) FROM screenshots WHERE timestamp >= ?", (today_ts,))
        screenshots_today = cur.fetchone()[0]

        # Screenshots this week
        week_start = today_start - timedelta(days=today_start.weekday())
        week_ts = format_timestamp(week_start)
        cur.execute("SELECT COUNT(*) FROM screenshots WHERE timestamp >= ?", (week_ts,))
        screenshots_this_week = cur.fetchone()[0]

        # Screenshots yesterday (for comparison)
        yesterday_start = today_start - timedelta(days=1)
        yesterday_ts = format_timestamp(yesterday_start)
        cur.execute("SELECT COUNT(*) FROM screenshots WHERE timestamp >= ? AND timestamp < ?", (yesterday_ts, today_ts))
        screenshots_yesterday = cur.fetchone()[0]

        # Calculate storage
        screenshots_dir = get_screenshots_dir()
        total_storage_bytes = 0
        file_sizes = []

        if screenshots_dir.exists():
            for f in screenshots_dir.iterdir():
                if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                    size = f.stat().st_size
                    total_storage_bytes += size
                    file_sizes.append(size)

        avg_file_size = int(total_storage_bytes / len(file_sizes)) if file_sizes else 0

    return {
        "total_screenshots": total_screenshots,
        "total_storage_bytes": total_storage_bytes,
        "compressed_count": compressed_count,
        "avg_file_size": avg_file_size,
        "screenshots_today": screenshots_today,
        "screenshots_yesterday": screenshots_yesterday,
        "screenshots_this_week": screenshots_this_week,
        "ocr_processed_count": ocr_processed_count,
    }


@router.get("/storage")
async def get_storage_analytics(
    days: int = Query(default=30, ge=7, le=365, description="Number of days to analyze"),
):
    """
    Get storage analytics including daily growth and size distribution.
    """
    with db.cursor() as cur:
        # Get daily storage data for the last N days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        daily_data = []

        # Build a lookup of file sizes by date from the database timestamps
        cur.execute(
            """
            SELECT timestamp, image_path
            FROM screenshots
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
            """,
            (format_timestamp(start_date),),
        )
        rows = cur.fetchall()

        # Group by date
        date_sizes: dict[str, list[int]] = {}
        for row in rows:
            ts = row[0]
            path = Path(row[1])
            if len(ts) >= 6:
                date_key = f"20{ts[0:2]}-{ts[2:4]}-{ts[4:6]}"
                if path.exists():
                    size = path.stat().st_size
                    if date_key not in date_sizes:
                        date_sizes[date_key] = []
                    date_sizes[date_key].append(size)

        # Fill in all dates
        current = start_date
        cumulative_bytes = 0

        # Get initial cumulative from before start date
        cur.execute("SELECT COUNT(*) FROM screenshots WHERE timestamp < ?", (format_timestamp(start_date),))
        initial_count = cur.fetchone()[0]

        # Estimate initial storage based on average file size
        if date_sizes:
            all_sizes = [s for sizes in date_sizes.values() for s in sizes]
            avg_size = sum(all_sizes) / len(all_sizes) if all_sizes else 100000
            cumulative_bytes = int(initial_count * avg_size)

        while current <= end_date:
            date_key = current.strftime("%Y-%m-%d")
            day_sizes = date_sizes.get(date_key, [])
            day_bytes = sum(day_sizes)
            cumulative_bytes += day_bytes

            daily_data.append(
                {
                    "date": date_key,
                    "screenshots": len(day_sizes),
                    "bytes_added": day_bytes,
                    "cumulative_bytes": cumulative_bytes,
                }
            )
            current += timedelta(days=1)

        # Get compression stats
        cur.execute("SELECT COUNT(*) FROM screenshots WHERE is_compressed = 1")
        compressed_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM screenshots WHERE is_compressed = 0")
        uncompressed_count = cur.fetchone()[0]

        cur.execute("SELECT SUM(original_size_bytes) FROM screenshots WHERE is_compressed = 1")
        original_bytes = cur.fetchone()[0] or 0

        # Get current compressed file sizes
        cur.execute("SELECT image_path FROM screenshots WHERE is_compressed = 1")
        compressed_current_bytes = 0
        for row in cur.fetchall():
            path = Path(row[0])
            if path.exists():
                compressed_current_bytes += path.stat().st_size

        bytes_saved = original_bytes - compressed_current_bytes if original_bytes > 0 else 0

        # Get largest files
        cur.execute(
            """
            SELECT id, image_path, timestamp
            FROM screenshots
            ORDER BY timestamp DESC
            LIMIT 100
            """
        )

        largest_files = []
        for row in cur.fetchall():
            path = Path(row[1])
            if path.exists():
                size = path.stat().st_size
                largest_files.append(
                    {
                        "id": row[0],
                        "path": row[1],
                        "timestamp": row[2],
                        "size_bytes": size,
                    }
                )

        # Sort by size and take top 10
        largest_files.sort(key=lambda x: x["size_bytes"], reverse=True)
        largest_files = largest_files[:10]

        # Storage by month
        cur.execute(
            """
            SELECT
                substr(timestamp, 1, 4) as month,
                COUNT(*) as count
            FROM screenshots
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
            """
        )

        storage_by_month = []
        for row in cur.fetchall():
            month_str = row[0]  # YYMM format
            if len(month_str) == 4:
                year = 2000 + int(month_str[0:2])
                month = int(month_str[2:4])
                storage_by_month.append(
                    {
                        "month": f"{year}-{month:02d}",
                        "count": row[1],
                    }
                )

    return {
        "daily_data": daily_data,
        "compression": {
            "compressed_count": compressed_count,
            "uncompressed_count": uncompressed_count,
            "original_bytes": original_bytes,
            "current_bytes": compressed_current_bytes,
            "bytes_saved": bytes_saved,
        },
        "largest_files": largest_files,
        "storage_by_month": storage_by_month,
    }


@router.get("/activity")
async def get_activity_analytics(
    weeks: int = Query(default=12, ge=1, le=52, description="Number of weeks for heatmap"),
):
    """
    Get activity analytics including heatmap data and distributions.
    """
    with db.cursor() as cur:
        # Get all screenshots from the last N weeks for heatmap
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)

        cur.execute(
            """
            SELECT timestamp
            FROM screenshots
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
            """,
            (format_timestamp(start_date),),
        )

        # Build heatmap data: {day_of_week: {hour: count}}
        heatmap: dict[int, dict[int, int]] = {i: {j: 0 for j in range(24)} for i in range(7)}
        hourly_totals: dict[int, int] = {i: 0 for i in range(24)}
        daily_totals: dict[int, int] = {i: 0 for i in range(7)}

        # Weekly data for the last N weeks
        weekly_data: dict[str, int] = {}

        for row in cur.fetchall():
            ts = row[0]
            dt = parse_timestamp(ts)
            day_of_week = dt.weekday()  # 0=Monday, 6=Sunday
            hour = dt.hour

            heatmap[day_of_week][hour] += 1
            hourly_totals[hour] += 1
            daily_totals[day_of_week] += 1

            # Week key for weekly trend
            week_start = dt - timedelta(days=dt.weekday())
            week_key = week_start.strftime("%Y-%m-%d")
            weekly_data[week_key] = weekly_data.get(week_key, 0) + 1

        # Convert heatmap to list format
        heatmap_data = []
        for day in range(7):
            for hour in range(24):
                count = heatmap[day][hour]
                if count > 0:  # Only include non-zero for efficiency
                    heatmap_data.append(
                        {
                            "day_of_week": day,
                            "hour": hour,
                            "count": count,
                        }
                    )

        # Convert distributions to sorted lists
        hourly_distribution = [{"hour": h, "count": hourly_totals[h]} for h in range(24)]
        daily_distribution = [{"day": d, "count": daily_totals[d]} for d in range(7)]

        # Weekly trend (sorted by date)
        weekly_trend = [{"week": k, "count": v} for k, v in sorted(weekly_data.items())]

        # Find peak times
        max_hour = max(hourly_totals.items(), key=lambda x: x[1])
        max_day = max(daily_totals.items(), key=lambda x: x[1])

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    return {
        "heatmap_data": heatmap_data,
        "hourly_distribution": hourly_distribution,
        "daily_distribution": daily_distribution,
        "weekly_trend": weekly_trend,
        "peak_hour": max_hour[0],
        "peak_day": day_names[max_day[0]],
        "total_in_period": sum(hourly_totals.values()),
    }


@router.get("/activity-week")
async def get_activity_week(
    week_offset: int = Query(
        default=0, ge=-52, le=0, description="Week offset from current week (0=current, -1=last week, etc.)"
    ),
):
    """
    Get activity data for a specific week.

    Returns hourly screenshot counts for each day of the specified week,
    suitable for a 7x24 heatmap calendar view.
    """
    with db.cursor() as cur:
        # Calculate the week's start and end dates
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        current_week_start = today - timedelta(days=today.weekday())  # Monday

        # Apply offset
        week_start = current_week_start + timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=7)

        start_ts = format_timestamp(week_start)
        end_ts = format_timestamp(week_end)

        cur.execute(
            """
            SELECT timestamp, id
            FROM screenshots
            WHERE timestamp >= ? AND timestamp < ?
            ORDER BY timestamp ASC
            """,
            (start_ts, end_ts),
        )

        # Build heatmap data: list of {date, day_of_week, hour, count, screenshot_ids}
        # Group by date and hour
        data_map: dict[str, dict[int, list[int]]] = {}  # date -> hour -> [screenshot_ids]

        for row in cur.fetchall():
            ts = row[0]
            screenshot_id = row[1]
            dt = parse_timestamp(ts)
            date_key = dt.strftime("%Y-%m-%d")
            hour = dt.hour

            if date_key not in data_map:
                data_map[date_key] = {h: [] for h in range(24)}
            data_map[date_key][hour].append(screenshot_id)

        # Build response with all 7 days
        heatmap_data: list[HeatmapCell] = []
        day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for day_offset in range(7):
            day_date = week_start + timedelta(days=day_offset)
            date_key = day_date.strftime("%Y-%m-%d")
            day_data = data_map.get(date_key, {h: [] for h in range(24)})

            for hour in range(24):
                ids = day_data.get(hour, [])
                heatmap_data.append(
                    {
                        "date": date_key,
                        "day_of_week": day_offset,
                        "day_label": day_labels[day_offset],
                        "hour": hour,
                        "count": len(ids),
                        "screenshot_ids": ids[:10],  # Limit to first 10 for preview
                    }
                )

        # Calculate totals for this week
        total_screenshots = sum(item["count"] for item in heatmap_data)

        # Find peak time this week
        max_item = max(heatmap_data, key=lambda x: x["count"]) if heatmap_data else None
        peak_info = None
        if max_item and max_item["count"] > 0:
            peak_info = {
                "day": max_item["day_label"],
                "hour": max_item["hour"],
                "count": max_item["count"],
            }

    return {
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": (week_end - timedelta(days=1)).strftime("%Y-%m-%d"),
        "week_offset": week_offset,
        "heatmap_data": heatmap_data,
        "total_screenshots": total_screenshots,
        "peak": peak_info,
    }


@router.get("/gaps")
async def get_gap_analytics(
    min_gap_minutes: int = Query(default=30, ge=5, le=1440, description="Minimum gap duration in minutes"),
    limit: int = Query(default=50, ge=10, le=200, description="Maximum gaps to return"),
):
    """
    Get timeline gaps (periods with no visible screenshots).

    Identifies gaps in recording, which could be due to system sleep,
    app not running, or incognito mode.

    A gap is marked as 'incognito' if there are hidden screenshots
    during the gap period (incognito saves screenshots as hidden).
    """
    with db.cursor() as cur:
        # Get VISIBLE screenshots only for gap detection
        cur.execute(
            """
            SELECT timestamp
            FROM screenshots
            WHERE is_hidden = 0
            ORDER BY timestamp ASC
            """
        )
        visible_rows = cur.fetchall()

        # Get HIDDEN screenshots for incognito detection
        cur.execute(
            """
            SELECT timestamp
            FROM screenshots
            WHERE is_hidden = 1
            ORDER BY timestamp ASC
            """
        )
        hidden_rows = cur.fetchall()

        if len(visible_rows) < 2:
            return {
                "gaps": [],
                "total_gap_time_seconds": 0,
                "longest_gap_seconds": 0,
                "avg_gap_seconds": 0,
                "gap_count": 0,
            }

        # Build list of hidden timestamps for checking incognito periods
        hidden_timestamps = []
        for (ts,) in hidden_rows:
            with contextlib.suppress(Exception):
                hidden_timestamps.append(parse_timestamp(ts))

        min_gap_seconds = min_gap_minutes * 60
        gaps = []

        prev_ts = visible_rows[0][0]

        for i in range(1, len(visible_rows)):
            curr_ts = visible_rows[i][0]

            prev_dt = parse_timestamp(prev_ts)
            curr_dt = parse_timestamp(curr_ts)

            gap_seconds = (curr_dt - prev_dt).total_seconds()

            if gap_seconds >= min_gap_seconds:
                # Check if there are hidden screenshots during this gap period
                # If so, it's an incognito period
                has_hidden_during_gap = False
                for hidden_dt in hidden_timestamps:
                    if prev_dt < hidden_dt < curr_dt:
                        has_hidden_during_gap = True
                        break

                gap_type = "incognito" if has_hidden_during_gap else "gap"

                gaps.append(
                    {
                        "start_time": prev_ts,
                        "end_time": curr_ts,
                        "duration_seconds": int(gap_seconds),
                        "type": gap_type,
                    }
                )

            prev_ts = curr_ts

        # Separate incognito and regular gaps, sorted by duration (longest first)
        incognito_gaps = sorted(
            [g for g in gaps if g["type"] == "incognito"], key=lambda x: x["duration_seconds"], reverse=True
        )
        regular_gaps = sorted(
            [g for g in gaps if g["type"] == "gap"], key=lambda x: x["duration_seconds"], reverse=True
        )

        # Interleave both types so both are always visible at the top
        # Pattern: regular, incognito, regular, incognito, ...
        interleaved: list[dict] = []
        i_reg, i_inc = 0, 0
        while len(interleaved) < limit and (i_reg < len(regular_gaps) or i_inc < len(incognito_gaps)):
            if i_reg < len(regular_gaps):
                interleaved.append(regular_gaps[i_reg])
                i_reg += 1
            if len(interleaved) < limit and i_inc < len(incognito_gaps):
                interleaved.append(incognito_gaps[i_inc])
                i_inc += 1

        gaps = interleaved

        # Calculate statistics
        total_gap_time = sum(g["duration_seconds"] for g in gaps)
        longest_gap = gaps[0]["duration_seconds"] if gaps else 0
        avg_gap = total_gap_time / len(gaps) if gaps else 0

    return {
        "gaps": gaps,
        "total_gap_time_seconds": total_gap_time,
        "longest_gap_seconds": longest_gap,
        "avg_gap_seconds": int(avg_gap),
        "gap_count": len(gaps),
    }


@router.get("/quality")
async def get_quality_analytics():
    """
    Get file quality and size distribution analytics.
    """
    screenshots_dir = get_screenshots_dir()

    file_sizes = []
    if screenshots_dir.exists():
        for f in screenshots_dir.iterdir():
            if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                file_sizes.append(f.stat().st_size)

    if not file_sizes:
        return {
            "avg_file_size": 0,
            "min_file_size": 0,
            "max_file_size": 0,
            "median_file_size": 0,
            "size_distribution": [],
            "total_files": 0,
        }

    file_sizes.sort()
    total_files = len(file_sizes)
    avg_size = sum(file_sizes) / total_files
    min_size = file_sizes[0]
    max_size = file_sizes[-1]
    median_size = file_sizes[total_files // 2]

    # Create size distribution buckets
    # Buckets: <50KB, 50-100KB, 100-200KB, 200-500KB, 500KB-1MB, >1MB
    buckets = [
        ("< 50 KB", 0, 50 * 1024),
        ("50-100 KB", 50 * 1024, 100 * 1024),
        ("100-200 KB", 100 * 1024, 200 * 1024),
        ("200-500 KB", 200 * 1024, 500 * 1024),
        ("500 KB - 1 MB", 500 * 1024, 1024 * 1024),
        ("> 1 MB", 1024 * 1024, float("inf")),
    ]

    size_distribution = []
    for label, min_bound, max_bound in buckets:
        count = sum(1 for s in file_sizes if min_bound <= s < max_bound)
        size_distribution.append(
            {
                "label": label,
                "count": count,
                "percentage": round(count / total_files * 100, 1),
            }
        )

    # Get compression stats
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM screenshots WHERE is_compressed = 1")
        compressed_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM screenshots WHERE is_compressed = 0")
        uncompressed_count = cur.fetchone()[0]

        cur.execute("SELECT SUM(original_size_bytes) FROM screenshots WHERE is_compressed = 1")
        original_total = cur.fetchone()[0] or 0

    return {
        "avg_file_size": int(avg_size),
        "min_file_size": min_size,
        "max_file_size": max_size,
        "median_file_size": median_size,
        "size_distribution": size_distribution,
        "total_files": total_files,
        "compression_stats": {
            "compressed_count": compressed_count,
            "uncompressed_count": uncompressed_count,
            "original_bytes_before_compression": original_total,
        },
    }


@router.get("/trends")
async def get_trends_analytics(
    days: int = Query(default=30, ge=7, le=365, description="Number of days to analyze"),
):
    """
    Get recording trends and patterns over time.
    """
    with db.cursor() as cur:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get daily screenshot counts
        cur.execute(
            """
            SELECT timestamp
            FROM screenshots
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
            """,
            (format_timestamp(start_date),),
        )

        daily_counts: dict[str, int] = {}
        for row in cur.fetchall():
            ts = row[0]
            if len(ts) >= 6:
                date_key = f"20{ts[0:2]}-{ts[2:4]}-{ts[4:6]}"
                daily_counts[date_key] = daily_counts.get(date_key, 0) + 1

        # Fill in missing days
        daily_data: list[DailyDataPoint] = []
        current = start_date
        while current <= end_date:
            date_key = current.strftime("%Y-%m-%d")
            daily_data.append(
                {
                    "date": date_key,
                    "count": daily_counts.get(date_key, 0),
                    "moving_avg": 0.0,
                }
            )
            current += timedelta(days=1)

        # Calculate moving average (7-day)
        for i, day in enumerate(daily_data):
            start_idx = max(0, i - 6)
            window = daily_data[start_idx : i + 1]
            day["moving_avg"] = round(sum(d["count"] for d in window) / len(window), 1)

        # Get sync and OCR stats over time
        cur.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN has_embedding = 1 THEN 1 ELSE 0 END) as synced,
                SUM(CASE WHEN has_ocr = 1 THEN 1 ELSE 0 END) as ocr_done
            FROM screenshots
            WHERE timestamp >= ?
            """,
            (format_timestamp(start_date),),
        )
        row = cur.fetchone()

        total_in_period = row[0] or 0
        synced_in_period = row[1] or 0
        ocr_in_period = row[2] or 0

        # Calculate averages
        days_with_data = len([d for d in daily_data if d["count"] > 0])
        avg_per_day = total_in_period / days if days > 0 else 0

        # Find best and worst days
        if daily_data:
            best_day = max(daily_data, key=lambda x: x["count"])
            worst_day_result = min(
                (d for d in daily_data if d["count"] > 0),
                key=lambda x: x["count"],
                default=None,
            )
            worst_day = worst_day_result
        else:
            best_day = None
            worst_day = None

    return {
        "daily_data": daily_data,
        "summary": {
            "total_screenshots": total_in_period,
            "synced_count": synced_in_period,
            "ocr_processed_count": ocr_in_period,
            "avg_per_day": round(avg_per_day, 1),
            "days_with_recordings": days_with_data,
            "best_day": {"date": best_day["date"], "count": best_day["count"]} if best_day else None,
            "worst_day": {"date": worst_day["date"], "count": worst_day["count"]} if worst_day else None,
        },
    }
