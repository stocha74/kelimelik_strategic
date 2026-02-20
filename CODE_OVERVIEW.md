# Code Overview

This repository contains a Turkish Scrabble/Kelimelik move generation and scoring toolkit made of three Python modules.

## 1) `kelimelik_engine1.py`
Core board engine:
- Word placement validation (`ilk_kelime_yerlestir`, `kelime_yerlestir`, `kelime_yerlestir_new`).
- Cross-word extraction and scoring (`kelime_kontrol`, `kelime_kontrol_new`, `kelime_kontrol_final`).
- Board bonus squares are included in final score calculation with letter/word multipliers and special bonuses.

In short: this file is responsible for applying moves to a 15x15 board, checking legal overlap/touch rules, generating words formed by the move, and computing final scores.

## 2) `dawg_helper.py`
Dictionary and candidate generation helper:
- Defines a minimal DAWG/TRIE-like structure (`DawgNode`, `Dawg`) for prefix traversal.
- Extracts existing horizontal/vertical board fragments (`extract_word_parts`).
- Computes free extension limits to left/right (or up/down) for each fragment (`compute_left_right_limits`).
- Generates possible full words by adding rack-letter prefixes/suffixes around fixed board fragments (`generate_candidates_for_word_part_with_board`).

In short: this file accelerates candidate generation by traversing dictionary prefixes instead of brute-force permutation against the entire dictionary.

## 3) `kelimelik_deterministikstratejik_ajan_dawg_ (1).py`
Deterministic strategic agent + Monte Carlo simulation:
- Loads and normalizes Turkish dictionary words.
- Builds `RackTrie` for fast “rack -> valid words” generation with caching (`lru_cache`).
- Computes legal move index and scores by calling engine functions (`hesapla_ana_dizin`).
- Simulates opponent responses with Monte Carlo (`monte_carlo_en_iyi_hamle`) and selects move maximizing our score gap.

In short: this file is the decision layer (AI policy) that uses the engine and trie acceleration to choose strong moves.

## Data Flow (high level)
1. Current board + rack letters are given to the strategic agent.
2. Candidate words/placements are generated (TRIE/DAWG + engine helpers).
3. Engine validates placements and computes score + penalties.
4. Monte Carlo estimates opponent best-response expectation.
5. Best move is selected based on objective (mainly score difference).
