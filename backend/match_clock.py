"""Scenario schedule: elapsed replay seconds are distinct from the football clock."""
HALF = 45 * 60
FIRST_ADDED = 2 * 60
SECOND_ADDED = 3 * 60
HALF_TIME_START = HALF + FIRST_ADDED
HALF_TIME_BREAK = 15 * 60
SECOND_HALF_START = HALF_TIME_START + HALF_TIME_BREAK
DURATION = SECOND_HALF_START + HALF + SECOND_ADDED
PLAYING_DURATION = DURATION - HALF_TIME_BREAK
DEMO_PRESS = SECOND_HALF_START + 14 * 60 + 30
DEMO_GOAL = SECOND_HALF_START + 15 * 60 + 30


def playing_second(second):
    return min(second, HALF_TIME_START) + max(0, second - SECOND_HALF_START)


def display_clock(second):
    if second < HALF_TIME_START:
        local, base = second, 0
    elif second < SECOND_HALF_START:
        local, base = HALF_TIME_START, 0
    else:
        local, base = second - SECOND_HALF_START, 45
    if local >= HALF:
        extra = local - HALF
        return '%s+%s:%02d' % (base + 45, extra // 60, extra % 60)
    return '%02d:%02d' % (base + local // 60, local % 60)


def clock_state(second):
    status = ('first_half' if second < HALF_TIME_START else 'half_time' if second < SECOND_HALF_START
              else 'second_half' if second < DURATION else 'full_time')
    period = 1 if second < SECOND_HALF_START else 2
    local = second if period == 1 else second - SECOND_HALF_START
    return dict(match_status=status, period=period, display_clock=display_clock(second),
                playing_second=playing_second(second),
                added_time=status in ('first_half', 'second_half') and local >= HALF,
                attacking_directions=dict(home=-1 if period == 1 else 1, away=1 if period == 1 else -1))


def schedule():
    return dict(half_seconds=HALF, first_added=FIRST_ADDED, second_added=SECOND_ADDED,
                half_time_start=HALF_TIME_START, half_time_break=HALF_TIME_BREAK,
                second_half_start=SECOND_HALF_START, duration=DURATION, playing_duration=PLAYING_DURATION)
