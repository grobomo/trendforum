#!/usr/bin/env python3
"""Date helper — compute dates programmatically instead of mental math.

Usage:
    python3 datehelper.py 'next monday'
    python3 datehelper.py 'tomorrow'
    python3 datehelper.py 'today'
    python3 datehelper.py 'next friday'
    python3 datehelper.py '2026-04-21'      # validates and echoes
    python3 datehelper.py 'this week'       # Mon-Sun of current week
    python3 datehelper.py 'next week'       # Mon-Sun of next week

Output: ISO dates + day names suitable for Graph API calendarView queries.
Timezone: America/Chicago (CDT/CST)
"""

import sys
from datetime import date, timedelta

DAYS = {
    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
    'friday': 4, 'saturday': 5, 'sunday': 6,
    'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
    'fri': 4, 'sat': 5, 'sun': 6,
}

def next_weekday(d: date, weekday: int) -> date:
    """Return the next occurrence of weekday (0=Mon) after date d."""
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return d + timedelta(days_ahead)

def parse_date_expr(expr: str) -> list[tuple[date, date]]:
    """Parse a date expression into (start, end) date ranges.
    Returns list of (start_date, end_date) where end is exclusive (for Graph API).
    """
    expr = expr.strip().lower()
    today = date.today()
    
    if expr == 'today':
        return [(today, today + timedelta(1))]
    
    if expr == 'tomorrow':
        tmrw = today + timedelta(1)
        return [(tmrw, tmrw + timedelta(1))]
    
    if expr == 'yesterday':
        yest = today - timedelta(1)
        return [(yest, yest + timedelta(1))]
    
    if expr == 'this week':
        # Monday through Sunday of current week
        mon = today - timedelta(today.weekday())
        sun = mon + timedelta(7)
        return [(mon, sun)]
    
    if expr == 'next week':
        mon = today - timedelta(today.weekday()) + timedelta(7)
        sun = mon + timedelta(7)
        return [(mon, sun)]
    
    # "next <day>" patterns
    for prefix in ('next ', 'this '):
        if expr.startswith(prefix):
            day_name = expr[len(prefix):]
            if day_name in DAYS:
                target = next_weekday(today, DAYS[day_name])
                return [(target, target + timedelta(1))]
    
    # Plain day name (treat as "next <day>")
    if expr in DAYS:
        target = next_weekday(today, DAYS[expr])
        return [(target, target + timedelta(1))]
    
    # ISO date string
    try:
        d = date.fromisoformat(expr)
        return [(d, d + timedelta(1))]
    except ValueError:
        pass
    
    # "in N days"
    if expr.startswith('in ') and expr.endswith(' days'):
        try:
            n = int(expr[3:-5].strip())
            target = today + timedelta(n)
            return [(target, target + timedelta(1))]
        except ValueError:
            pass
    
    print(f"ERROR: Can't parse '{expr}'", file=sys.stderr)
    print("Supported: today, tomorrow, yesterday, next monday, this week, next week, YYYY-MM-DD, in N days", file=sys.stderr)
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print(f"Today is: {date.today().isoformat()} ({date.today().strftime('%A')})")
        print(f"\nUsage: {sys.argv[0]} '<expression>'")
        print("Examples: 'today', 'tomorrow', 'next monday', 'this week', '2026-04-20'")
        sys.exit(0)
    
    expr = ' '.join(sys.argv[1:])
    ranges = parse_date_expr(expr)
    
    for start, end in ranges:
        days = (end - start).days
        if days == 1:
            print(f"Date: {start.isoformat()} ({start.strftime('%A')})")
            print(f"Graph API range: startDateTime={start.isoformat()}T00:00:00Z&endDateTime={end.isoformat()}T00:00:00Z")
        else:
            print(f"Range: {start.isoformat()} ({start.strftime('%A')}) to {(end - timedelta(1)).isoformat()} ({(end - timedelta(1)).strftime('%A')})")
            print(f"Graph API range: startDateTime={start.isoformat()}T00:00:00Z&endDateTime={end.isoformat()}T00:00:00Z")

if __name__ == '__main__':
    main()
