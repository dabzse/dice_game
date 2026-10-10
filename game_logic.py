"""
game_logic.py — Core game logic for the dice game.

Scoring model
─────────────
Each player has one score sheet.  The sheet has the same categories every
round, and EVERY category resets at the start of each new round — i.e. a
player may score Full House in round 1 AND round 3.  The sheet stores the
cumulative total per category (sum across all rounds) as well as the
per-round history for display.

Upper section (Ones … Sixes)
    • Each round the player may score any upper category once.

Chance bonus
    • If the cumulative total of Chance reaches ≥ 63 the player earns
        a one-time +35 bonus (awarded the moment the threshold is crossed).

Lower section combinations (scored once per round)
    Three of a Kind  → 25 pts  (three or more of the same face)
    Four of a Kind   → 30 pts  (four or more of the same face)
    Full House       → 25 pts  (three of one face + two of another)
    Small Straight   → 30 pts  (1-2-3-4 or 2-3-4-5 or 3-4-5-6 in any order)
    Large Straight   → 40 pts  (1-2-3-4-5 or 2-3-4-5-6 in any order)
    Top Score        → 50 pts  (all five dice the same)
    Chance           → sum of all five dice

Mutual-exclusivity within a turn (highest wins):
    Top Score beats Four of a Kind beats Three of a Kind
    Full House beats Three of a Kind

Round-end Top Score bonus
    After every round the player(s) with the highest score achieved in that
    round earn an additional +50 bonus (if score > 0).
"""

import secrets
from collections import Counter

# –––– Category names

UPPER_CATEGORIES = ["Ones", "Twos", "Threes", "Fours", "Fives", "Sixes"]

# Category name constants
CAT_THREE_OF_A_KIND = "Three of a Kind"
CAT_FOUR_OF_A_KIND = "Four of a Kind"
CAT_FULL_HOUSE = "Full House"
CAT_TOP_SCORE = "Top Score"
CAT_SMALL_STRAIGHT = "Small Straight"
CAT_LARGE_STRAIGHT = "Large Straight"
CAT_CHANCE = "Chance"


LOWER_CATEGORIES = [
    CAT_THREE_OF_A_KIND,
    CAT_FOUR_OF_A_KIND,
    CAT_FULL_HOUSE,
    CAT_SMALL_STRAIGHT,
    CAT_LARGE_STRAIGHT,
    CAT_TOP_SCORE,
    CAT_CHANCE,
]

ALL_CATEGORIES = UPPER_CATEGORIES + LOWER_CATEGORIES

CHANCE_BONUS_THRESHOLD = 63
CHANCE_BONUS_VALUE = 35
UPPER_BONUS_THRESHOLD = CHANCE_BONUS_THRESHOLD
UPPER_BONUS_VALUE = CHANCE_BONUS_VALUE

NUM_DICE = 5
MAX_ROLLS = 3


# –––– Dice helpers


def roll_dice(num: int = NUM_DICE) -> list[int]:
    return [secrets.randbelow(6) + 1 for _ in range(num)]


def reroll(current: list[int], held: list[bool]) -> list[int]:
    return [v if k else secrets.randbelow(6) + 1 for v, k in zip(current, held)]


# –––– Individual scoring functions


def score_upper(dice: list[int], face: int) -> int:
    return sum(d for d in dice if d == face)


def score_three_of_a_kind(dice: list[int]) -> int:
    return 25 if any(v >= 3 for v in Counter(dice).values()) else 0


def score_four_of_a_kind(dice: list[int]) -> int:
    return 30 if any(v >= 4 for v in Counter(dice).values()) else 0


def score_full_house(dice: list[int]) -> int:
    return 25 if sorted(Counter(dice).values()) == [2, 3] else 0


def score_large_straight(dice: list[int]) -> int:
    # Large straight = 1-2-3-4-5 or 2-3-4-5-6, any order (40 pts)
    sorted_unique = sorted(set(dice))
    return (
        40
        if sorted_unique == [1, 2, 3, 4, 5] or sorted_unique == [2, 3, 4, 5, 6]
        else 0
    )


def score_small_straight(dice: list[int]) -> int:
    # Small straight = 1-2-3-4 or 2-3-4-5 or 3-4-5-6, any order (30 pts)
    dice_set = set(dice)
    small_straights = [{1, 2, 3, 4}, {2, 3, 4, 5}, {3, 4, 5, 6}]
    return 30 if any(pattern.issubset(dice_set) for pattern in small_straights) else 0


def score_top_score(dice: list[int]) -> int:
    return 50 if len(set(dice)) == 1 else 0


def score_chance(dice: list[int]) -> int:
    return sum(dice)


def calculate_score(category: str, dice: list[int]) -> int:
    if category == "Ones":
        return score_upper(dice, 1)
    if category == "Twos":
        return score_upper(dice, 2)
    if category == "Threes":
        return score_upper(dice, 3)
    if category == "Fours":
        return score_upper(dice, 4)
    if category == "Fives":
        return score_upper(dice, 5)
    if category == "Sixes":
        return score_upper(dice, 6)
    if category == CAT_THREE_OF_A_KIND:
        return score_three_of_a_kind(dice)
    if category == CAT_FOUR_OF_A_KIND:
        return score_four_of_a_kind(dice)
    if category == CAT_FULL_HOUSE:
        return score_full_house(dice)
    if category == CAT_SMALL_STRAIGHT:
        return score_small_straight(dice)
    if category == CAT_LARGE_STRAIGHT:
        return score_large_straight(dice)
    if category == CAT_TOP_SCORE:
        return score_top_score(dice)
    if category == CAT_CHANCE:
        return score_chance(dice)
    return 0


def get_matching_scores(dice: list[int], available_cats: set[str]) -> dict[str, int]:
    """
    Return {category: score} for available categories that score > 0,
    with mutual-exclusivity applied:
        Top Score      → excludes Four of a Kind and Three of a Kind
        Four of a Kind → excludes Three of a Kind
        Full House     → excludes Three of a Kind
        Large Straight → excludes Small Straight
    """
    raw = {
        cat: calculate_score(cat, dice)
        for cat in ALL_CATEGORIES
        if cat in available_cats
    }

    excluded: set[str] = set()
    if raw.get(CAT_TOP_SCORE, 0) > 0:
        excluded |= {CAT_FOUR_OF_A_KIND, CAT_THREE_OF_A_KIND}
    elif raw.get(CAT_FOUR_OF_A_KIND, 0) > 0:
        excluded.add(CAT_THREE_OF_A_KIND)
    if raw.get(CAT_FULL_HOUSE, 0) > 0:
        excluded.add(CAT_THREE_OF_A_KIND)
    if raw.get("Large Straight", 0) > 0:
        excluded.add("Small Straight")

    return {cat: v for cat, v in raw.items() if cat not in excluded and v > 0}


# –––– Score sheet


class ScoreSheet:
    """
    Tracks one player's cumulative scores.

    Data layout
    ───────────
    self.totals   — {category: int}  running total across all rounds
    self.history  — {category: [round1_val, round2_val, …]}  per-round detail
                    The list length always matches self.completed_rounds;
                    entries are 0 for categories not scored in that round.
    self.dice_history — [[d1,d2,d3,d4,d5], …]  dice used at moment of final scoring
                        per completed round (index aligned with history).
    self.used_this_round — set of categories already scored in the current round
    self.completed_rounds — int; number of rounds fully written to history
    self.current_round_dice — list[int] | None; snapshot of the dice at last
                              scoring action in the ongoing turn; used when
                              finalize_round is called to populate dice_history.

    The chance-bonus flag is one-time: set to True when chance_total >= 63.
    The top_score_bonus accumulates +50 each time the player wins the
    round-end top-score award.
    """

    def __init__(self) -> None:
        self.totals: dict[str, int] = dict.fromkeys(ALL_CATEGORIES, 0)
        self.history: dict[str, list[int]] = {cat: [] for cat in ALL_CATEGORIES}
        self.dice_history: list[list[int]] = []
        self.used_this_round: set[str] = set()
        self.completed_rounds: int = 0
        self.current_round_dice: list[int] | None = None
        self.chance_bonus_earned: bool = False
        self.top_score_bonus_history: list[int] = []

    @property
    def upper_bonus_earned(self) -> bool:
        return self.chance_bonus_earned

    @upper_bonus_earned.setter
    def upper_bonus_earned(self, val: bool) -> None:
        self.chance_bonus_earned = val

    @property
    def top_score_bonus(self) -> int:
        return sum(self.top_score_bonus_history)

    def round_score(self, round_num: int) -> int:
        """Sum of category points scored in round_num (1-indexed)."""
        idx = round_num - 1
        return sum(
            self.history[cat][idx]
            for cat in ALL_CATEGORIES
            if idx < len(self.history[cat])
        )

    def round_upper_subtotal(self, round_num: int) -> int:
        """Upper section subtotal in round_num (1-indexed)."""
        idx = round_num - 1
        return sum(
            self.history[cat][idx]
            for cat in UPPER_CATEGORIES
            if idx < len(self.history[cat])
        )

    def round_lower_total(self, round_num: int) -> int:
        """Lower section total in round_num (1-indexed)."""
        idx = round_num - 1
        return sum(
            self.history[cat][idx]
            for cat in LOWER_CATEGORIES
            if idx < len(self.history[cat])
        )

    def round_total(self, round_num: int) -> int:
        """Total score in round_num (1-indexed), including round top score bonus if earned."""
        idx = round_num - 1
        r_cat = self.round_score(round_num)
        r_ts = (
            self.top_score_bonus_history[idx]
            if idx < len(self.top_score_bonus_history)
            else 0
        )
        return r_cat + r_ts

    # –––– per-round management

    def begin_round(self) -> None:
        """Call at the start of each player's turn to reset per-round tracking."""
        self.used_this_round.clear()
        self.current_round_dice = None

    def capture_dice(self, dice: list[int]) -> None:
        """Snapshot the dice at the moment of scoring (overwritten on each scoring action)."""
        self.current_round_dice = list(dice)

    def finalize_round(self) -> None:
        """
        Append 0 entries to history for every category NOT scored this round,
        so that each category has exactly one entry per completed round.
        Also appends the captured dice snapshot (or [0]*5 if none captured)
        to dice_history.  Increments completed_rounds.
        """
        for cat in ALL_CATEGORIES:
            if cat not in self.used_this_round:
                self.history[cat].append(0)
            # (scored categories already had their value appended by record())
        self.dice_history.append(
            list(self.current_round_dice) if self.current_round_dice else [0] * NUM_DICE
        )
        self.completed_rounds += 1

    def is_available(self, category: str) -> bool:
        """True if the player has NOT yet scored this category in the current round."""
        return category not in self.used_this_round

    def available_categories(self) -> list[str]:
        return [c for c in ALL_CATEGORIES if self.is_available(c)]

    # –––– recording

    def record(self, category: str, value: int) -> None:
        if not self.is_available(category):
            raise ValueError(f"'{category}' already scored this round.")

        self.used_this_round.add(category)
        self.totals[category] += value
        self.history[category].append(value)

        # Check one-time chance bonus
        if (
            not self.chance_bonus_earned
            and self.chance_total() >= CHANCE_BONUS_THRESHOLD
        ):
            self.chance_bonus_earned = True

    # –––– totals

    def upper_subtotal(self) -> int:
        return sum(self.totals[c] for c in UPPER_CATEGORIES)

    def chance_total(self) -> int:
        return self.totals.get(CAT_CHANCE, 0)

    def chance_bonus(self) -> int:
        return (
            CHANCE_BONUS_VALUE
            if (
                self.chance_bonus_earned
                or self.chance_total() >= CHANCE_BONUS_THRESHOLD
            )
            else 0
        )

    def upper_bonus(self) -> int:
        return self.chance_bonus()

    def lower_total(self) -> int:
        return sum(self.totals[c] for c in LOWER_CATEGORIES)

    def grand_total(self) -> int:
        return (
            self.upper_subtotal()
            + self.lower_total()
            + self.chance_bonus()
            + self.top_score_bonus
        )


# –––– Player


class Player:
    def __init__(self, name: str) -> None:
        self.name = name
        self.sheet = ScoreSheet()
        self.init_roll: int | None = None

    def __repr__(self) -> str:
        return f"Player({self.name!r}, total={self.sheet.grand_total()})"


# –––– Game state


class GameState:
    def __init__(self, players: list[Player], num_rounds: int = 6) -> None:
        self.players = players
        self.num_rounds = num_rounds
        self.current_round = 1
        self.current_player_index = 0
        self.dice: list[int] = [1] * NUM_DICE
        self.held: list[bool] = [False] * NUM_DICE
        self.rolls_used = 0
        self.phase = "init_roll"  # "init_roll" | "playing" | "game_over"
        self.last_top_score_winners: list[Player] = []

    # –––– Init-roll (turn order)

    def do_init_roll(self, player: Player) -> tuple[list[int], int]:
        dice = roll_dice(NUM_DICE)
        total = sum(dice)
        player.init_roll = total
        return dice, total

    def all_init_rolls_done(self) -> bool:
        return all(p.init_roll is not None for p in self.players)

    def finalise_order(self) -> None:
        self.players.sort(
            key=lambda p: p.init_roll if p.init_roll is not None else -1,
            reverse=True,
        )
        self.current_player_index = 0
        self.current_round = 1
        self.phase = "playing"
        self._start_turn()

    # –––– Turn mechanics

    def _start_turn(self) -> None:
        self.dice = [1] * NUM_DICE
        self.held = [False] * NUM_DICE
        self.rolls_used = 0
        if self.current_player_index > 0:
            self.last_top_score_winners = []
        # Reset per-round availability for the current player
        self.current_player().sheet.begin_round()

    def current_player(self) -> Player:
        return self.players[self.current_player_index]

    def can_roll(self) -> bool:
        return self.rolls_used < MAX_ROLLS and self.phase == "playing"

    def roll(self) -> list[int]:
        if not self.can_roll():
            raise RuntimeError("Cannot roll: limit reached or wrong phase.")

        self.dice = (
            roll_dice() if self.rolls_used == 0 else reroll(self.dice, self.held)
        )
        self.rolls_used += 1

        return list(self.dice)

    def toggle_hold(self, index: int) -> None:
        if self.rolls_used > 0:
            self.held[index] = not self.held[index]

    # –––– Scoring

    def score_and_advance(self, category: str) -> int:
        if self.rolls_used == 0:
            raise RuntimeError("Must roll at least once before scoring.")

        player = self.current_player()
        value = calculate_score(category, self.dice)
        player.sheet.capture_dice(self.dice)
        player.sheet.record(category, value)
        self._advance_turn()

        return value

    def score_all_matching(self) -> dict[str, int]:
        """
        Auto-score matching lower-section combinations for the current turn,
        plus upper-section categories only when all 5 dice show that face.
        Advances the turn only if at least one category was scored.
        Returns {category: score}.  If the dict is empty the turn was NOT advanced.
        """
        if self.rolls_used == 0:
            raise RuntimeError("Must roll at least once before scoring.")

        player = self.current_player()
        available = {c for c in ALL_CATEGORIES if player.sheet.is_available(c)}
        all_matched = get_matching_scores(self.dice, available)

        counts = Counter(self.dice)
        recorded: dict[str, int] = {}
        for cat, value in all_matched.items():
            if cat in LOWER_CATEGORIES:
                player.sheet.record(cat, value)
                recorded[cat] = value
            else:
                # Upper: auto-score only if all 5 dice are that face
                face = UPPER_CATEGORIES.index(cat) + 1
                if counts[face] == 5:
                    player.sheet.record(cat, value)
                    recorded[cat] = value

        if recorded:
            player.sheet.capture_dice(self.dice)
            self._advance_turn()
        return recorded

    # –––– Turn / round advancement

    def _advance_turn(self) -> None:
        # The player whose turn is ending finalizes their round's history
        self.current_player().sheet.finalize_round()
        self.current_player_index += 1
        if self.current_player_index >= len(self.players):
            self._award_top_score()
            self.current_player_index = 0
            self.current_round += 1
            if self.current_round > self.num_rounds:
                # Clear per-round availability flags so cumulative view shows
                # consistent "all used or available" coloring after the end.
                for p in self.players:
                    p.sheet.used_this_round.clear()
                self.phase = "game_over"
                return
        self._start_turn()

    def _award_top_score(self) -> None:
        scores = [(p, p.sheet.round_score(self.current_round)) for p in self.players]
        best = max((s for _, s in scores), default=0)
        if best > 0:
            winners = [p for p, s in scores if s == best]
            for p in self.players:
                p.sheet.top_score_bonus_history.append(50 if p in winners else 0)
            self.last_top_score_winners = winners
        else:
            for p in self.players:
                p.sheet.top_score_bonus_history.append(0)
            self.last_top_score_winners = []

    # –––– End-game

    def skip_to_end(self) -> None:
        """Force game over immediately (used by 'skip remaining turns' button)."""
        # Finalize the history for the player whose turn was cut short
        # (any category not recorded this turn gets a 0 pad entry)
        if self.phase == "playing":
            # If the mid-turn player has already rolled, capture their dice too
            if self.rolls_used > 0:
                self.current_player().sheet.capture_dice(self.dice)
            self.current_player().sheet.finalize_round()
        # Clear per-round flags for all players
        for p in self.players:
            p.sheet.used_this_round.clear()
        self.phase = "game_over"

    def winner(self) -> Player:
        return max(self.players, key=lambda p: p.sheet.grand_total())

    def rankings(self) -> list[tuple[int, Player]]:
        sp = sorted(self.players, key=lambda p: p.sheet.grand_total(), reverse=True)
        result, rank = [], 1
        for i, p in enumerate(sp):
            if i > 0 and p.sheet.grand_total() < sp[i - 1].sheet.grand_total():
                rank = i + 1
            result.append((rank, p))
        return result
