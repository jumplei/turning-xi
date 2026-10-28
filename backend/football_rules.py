"""Small, explicit rule-state helpers; not a complete referee or tracking system."""
from dataclasses import dataclass, field

NO_OFFSIDE_RESTARTS = frozenset({'goal_kick', 'corner', 'throw_in'})
MAX_SUBSTITUTES = 5
MAX_SUB_WINDOWS = 3


def offside_offence(receiver_x, ball_x, opponent_x, direction=1, *, involved=True, direct_restart=None):
    """Point-position approximation at a teammate's touch, with active receipt of the pass."""
    if direction not in (-1, 1) or len(opponent_x) < 2:
        raise ValueError('Need an attack direction and at least two opponents')
    if not involved or direct_restart in NO_OFFSIDE_RESTARTS:
        return False
    attack = lambda x: x if direction == 1 else 100-x
    receiver, ball = attack(receiver_x), attack(ball_x)
    second_last = sorted((attack(x) for x in opponent_x), reverse=True)[1]
    return receiver > 50 and receiver > ball and receiver > second_last


@dataclass
class Roster:
    active: set = field(default_factory=lambda: set(range(11)))
    bench: set = field(default_factory=lambda: set(range(11, 20)))
    withdrawn: set = field(default_factory=set)
    dismissed: set = field(default_factory=set)
    cautions: dict = field(default_factory=dict)
    dismissal_reasons: dict = field(default_factory=dict)
    keeper: int = 0
    substitutions: int = 0
    windows: int = 0

    @property
    def outfield(self):
        return sorted(self.active - {self.keeper})

    @property
    def can_continue(self):
        return len(self.active) >= 7

    def caution(self, player):
        if player not in self.active or self.cautions.get(player, 0) >= 2:
            raise ValueError('A caution requires an eligible on-field player')
        self.cautions[player] = self.cautions.get(player, 0) + 1
        return self.cautions[player] == 2

    def dismiss(self, player, reason='direct_red'):
        if player not in self.active:
            raise ValueError('Player is not on the pitch')
        if reason == 'second_yellow' and self.cautions.get(player) != 2:
            raise ValueError('Second-yellow dismissal requires two cautions')
        self.active.remove(player)
        self.dismissed.add(player)
        self.dismissal_reasons[player] = reason
        if player == self.keeper and self.active:
            self.keeper = min(self.active)  # an outfielder takes over until a legal keeper substitution

    def substitute(self, changes, *, half_time=False):
        """Validate a whole stoppage's batch atomically, then spend one window."""
        if not changes or len({a for a,b in changes}) != len(changes) or len({b for a,b in changes}) != len(changes):
            raise ValueError('Invalid substitution batch')
        if self.substitutions+len(changes) > MAX_SUBSTITUTES or (not half_time and self.windows >= MAX_SUB_WINDOWS):
            raise ValueError('Substitution allowance exceeded')
        if any(off not in self.active or on not in self.bench for off,on in changes):
            raise ValueError('Player is not eligible for this substitution')
        for off,on in changes:
            self.active.remove(off)
            self.bench.remove(on)
            self.active.add(on)
            self.withdrawn.add(off)
            if off == self.keeper or on == 11:  # bench #12 is the reserve goalkeeper
                self.keeper = on
        self.substitutions += len(changes)
        self.windows += not half_time

    def as_dict(self):
        return dict(active=sorted(self.active), bench=sorted(self.bench), withdrawn=sorted(self.withdrawn),
                    dismissed=sorted(self.dismissed), cautions=dict(self.cautions), keeper=self.keeper,
                    dismissal_reasons=dict(self.dismissal_reasons), substitutions=self.substitutions,
                    windows=self.windows, can_continue=self.can_continue)
