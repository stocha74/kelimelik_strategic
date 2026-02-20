# Detailed Code Overview

This repository implements a **Kelimelik (Turkish Scrabble-like) move engine + strategic agent**.
The code is organized around three Python modules:

- `kelimelik_engine1.py`: low-level game rules, placement checks, and scoring.
- `dawg_helper.py`: DAWG/TRIE-based candidate generation around fixed board fragments.
- `kelimelik_deterministikstratejik_ajan_dawg_ (1).py`: high-level move selection using deterministic scoring + Monte Carlo-style opponent simulation.

---

## 1) `kelimelik_engine1.py` — Game engine internals

This file is the rule/scoring core. It handles:

1. **Word placement mechanics**
   - First move placement helper: `ilk_kelime_yerlestir(...)`.
   - General placement validation: `kelime_yerlestir(...)`.
   - Extended variant with rack-origin tracking: `kelime_yerlestir_new(...)`.

2. **Word formation after placement**
   - `kelime_kontrol(...)` and newer variants build words formed by newly placed letters (main word + perpendicular words).
   - It scans board cells in both directions to find contiguous segments and merges existing board letters with newly placed letters.

3. **Scoring model**
   - Base score from letter values (`harf_puanlari`).
   - Additional board bonus handling via `tahta_puanlari2` (letter multipliers, word multipliers, and a special bonus code like `25`).
   - Returns final score (`nihai_puan`) along with formed words.

### Validation behavior and return conventions

- Placement helpers return either:
  - list(s) of letters consumed from rack, or
  - numeric error codes in invalid scenarios (e.g., no adjacency/contact, collision mismatch, out-of-bounds).
- The logic explicitly enforces **touching existing structure** for non-initial plays by checking a virtual border around the proposed word.

### Practical notes

- The board is treated as a **15x15 grid** where empty cells are `""`.
- Orientation handling is mostly with `"h"/"H"` vs vertical fallback.
- Some versions are iterative evolutions of the same logic (`_new`, `_final`) and coexist in the file.

---

## 2) `dawg_helper.py` — Dictionary index and anchored candidate generation

This module provides faster lexical generation than brute-force permutation over full dictionary.

## Core structures

- `DawgNode` stores:
  - `children`: outgoing edges keyed by character.
  - `is_word`: terminal marker.
- `Dawg` supports incremental insertion of dictionary words.
- `build_dawg_from_dictionary(...)` builds the full index from a word list.

## Board-driven candidate workflow

1. **Extract anchored fragments from board** (`extract_word_parts`)  
   Scans horizontally and vertically, returning contiguous non-empty fragments with start coordinates and orientation.

2. **Compute extension limits** (`compute_left_right_limits`)  
   For each fragment, computes how many empty cells are available before/after it (left-right or up-down depending on orientation).

3. **Generate compatible words around fixed fragment**
   - `_walk_fixed`: traverse trie using existing board fragment.
   - `_dfs_prefix_then_fixed`: enumerate rack-based prefixes that can precede fragment, then append suffixes.
   - `_dfs_suffix`: recursive suffix expansion limited by remaining slots and rack counts.
   - `generate_candidates_for_word_part_with_board`: emits `(word, x0, y0, orientation)` tuples suitable for engine placement checks.

### Important caveat

- `generate_candidates_for_word_part(...)` is intentionally a placeholder and raises `RuntimeError`; actual usage should call `generate_candidates_for_word_part_with_board(...)`.

---

## 3) `kelimelik_deterministikstratejik_ajan_dawg_ (1).py` — Strategic layer

This module orchestrates high-level move choice.

## A) Dictionary preprocessing

- Reads a Turkish word list.
- Normalizes Turkish characters to uppercase-compatible forms (`i/ı/ğ/ş/ö/ü/ç` handling).
- Filters dictionary:
  - `trim_dictionary(...)`: excludes words impossible under stock constraints.
  - `remove_long_words(...)`: hard cap (default 11 letters).

## B) Rack trie for fast rack→word expansion

- `RackTrie` is a trie optimized for generating all words buildable from a rack.
- Uses:
  - multiset rack signature (`sorted` letters),
  - `Counter` for letter availability,
  - `@lru_cache` to memoize results by rack signature and length limits.
- `words_from_rack_with_orientations(...)` returns engine-compatible tuples in both orientations.

This is the major performance improvement compared with scanning entire dictionary each simulation step.

## C) Move index computation (`hesapla_ana_dizin`)

The function builds and scores candidate placements:

1. Extract current board word pieces.
2. Build candidate words from board anchors + rack.
3. Optionally use `RackTrie` (`dawg` argument) for fast rack word generation.
4. Place and evaluate each candidate through engine function calls.
5. Keep only valid moves and compute feature metrics:
   - total move score,
   - score per letter,
   - disadvantage metric,
   - disadvantage/score ratio.
6. Sort move list primarily by score.

## D) Monte Carlo style opponent-response estimation

`monte_carlo_en_iyi_hamle(...)` evaluates our top candidate(s) by simulating opponent racks:

1. Apply our candidate move on a temporary board.
2. Draw opponent rack from remaining bag.
3. Let opponent take a single best move (using engine helper routines).
4. Repeat simulations and estimate opponent mean response score.
5. Select our move maximizing `our_score - opponent_expected_score`.

### Architectural note

- The file contains multiple historical definitions of `monte_carlo_en_iyi_hamle`; in Python, the **last definition wins** at runtime.

---

## End-to-end flow (how modules interact)

1. **Input**: board state, bonus board, rack letters, dictionary/stock.
2. **Candidate generation**:
   - board-anchor-based generation (`dawg_helper`) and/or rack-trie expansion (`RackTrie`).
3. **Legality + scoring**:
   - `kelimelik_engine1.py` validates placement interactions and computes final score with bonuses.
4. **Ranking**:
   - strategic module builds `ana_dizin` sorted by score-based criteria.
5. **Lookahead**:
   - Monte Carlo opponent simulation adjusts decision by expected counterplay.
6. **Output**:
   - selected move and associated statistics.

---

## Current limitations / refactor opportunities

- Hardcoded dictionary path in strategic file reduces portability.
- Duplicate/evolved functions in engine and strategy files make maintenance harder.
- Some debug prints remain; optional logging abstraction would improve clarity.
- Placeholder API in `dawg_helper.py` should be either implemented fully or removed.

