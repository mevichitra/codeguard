# Ground-truth check

A manual check of the harness's ground truth (the line diff of `linemap.py`) on a
seeded, stratified sample of 100 CodeGuard findings from the corpus replays
(`results/corpus-v3`), drawn by `gt_sample.py`: 20 in each of five strata.

| Stratum | What the harness says | Sampled from |
|---|---|---|
| `edited` | persisting, on an edited line | persisting findings whose line was edited |
| `known_but_new` | persisting, unchanged line, same path | persisting findings that SonarQube or CodeGuard report as new |
| `new_but_matched` | introduced | introduced findings that a content scheme matched to an old one (57 in the corpus) |
| `agree_known` | persisting | every content scheme agrees (control) |
| `agree_new` | introduced | every content scheme agrees (control; 1,917 in the corpus) |

## Files

- `sample.csv`: the key. One row per finding with the stratum, the harness's answer
  (`truth`) and the content schemes that disagree with it; `item` links to the blinded
  items.
- `sample.md`: the same findings for reading, with the harness's answer shown.
- `items.json`: the blinded items the raters saw: shuffled under neutral ids, without the
  harness's answer, the stratum or any scheme's outcome.
- `human_labels_round1.json`: the human rater's first pass, all 100 items.
- `agent_labels_round1.json`, `agent_labels_introduced_round2.json`: the agent rater's
  labels, with a one-sentence reason each.
- `human_adjudication.json`: the human rater's answers on the 14 items the agent flagged
  as harness errors.
- `adjudicated.json`: the final verdict per item and where it came from (`source`).
- `agreement.md`: the scores, from `gt_agreement.py`.

## How it was done

1. **Round 1.** The human rater labelled all 100 items on a labelling page, and an LLM
   agent labelled them independently, reading only `items.json`. Neither saw the other's
   labels or the harness's answer.
2. **A flaw in round 1.** For the 40 introduced items the page and `items.json` showed no
   code from before the commit, only the diff, which was empty near the line for many of
   them. Neither rater could judge whether those issues existed before. The human
   rater's round-1 labels on introduced items are therefore not used; the 60 pair labels
   are.
3. **Round 2.** `items.json` now gives each introduced item the old code at the same
   place (found with the line map). The agent relabelled the 40 introduced items from it,
   with instructions that no longer assumed an untouched line means an issue existed.
4. **Human confirmation.** The human rater checked each of the 14 items where the agent
   said the harness was wrong (13 introduced items it called "existed" and one pair it
   called "different"), seeing the agent's reason, and agreed on all 14.
5. **Rule re-runs.** Three of those 14 (F036, F065, F076) are whole-function rules
   (complexity, nesting) whose flagged line was unchanged. Re-running CodeGuard on the
   file before and after the commit shows the function was not reported before: the
   commit pushed it over the limit, so the finding is new and the harness was right.
   Both raters had judged from an excerpt that did not show the changed lines.

The 27 introduced items the agent labelled "new" in round 2 had no human check.

## Result

The harness's ground truth holds for 59 of 60 pairs (98.3%, Wilson 95% CI 91.1–99.7)
and 30 of 40 introduced items (75.0%, 59.8–85.8). The errors concentrate in
`new_but_matched`: 10 of 20 (29.9–70.1) are findings that persisted while the line diff
lost them (a line edited past the similarity threshold, or moved out of a removed block),
so the scheme that matched them was right. `agreement.md` has the corrected hidden rates
per scheme.

Regenerate the scores with:

```bash
G=research/finding_identity/paper/ground_truth_check
python -m research.finding_identity.gt_agreement --human $G/human_labels_round1.json \
    --human-kind pair --agent $G/agent_labels_round1.json \
    --agent $G/agent_labels_introduced_round2.json --adjudicated $G/adjudicated.json \
    --results research/finding_identity/results/corpus-v3
```
