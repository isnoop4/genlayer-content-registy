# Content Originality Registry — GenLayer Intelligent Contract

An on-chain originality checker where GenLayer's leader/validator
consensus fetches real web sources itself and cross-verifies a piece
of content against them — settling `ORIGINAL` / `DERIVATIVE` /
`PLAGIARIZED` / `ERROR` on-chain, grounded in verifiable evidence
rather than a claim the caller could fabricate.

## Project Summary

Detecting plagiarism today usually relies on centralized services
(Turnitin, Copyscape) or shallow keyword matching. This project lets
GenLayer's AI validator set fetch an external source itself and judge
whether a registered piece of content is original, derivative, or
plagiarized — settling a verdict on-chain, with every validator
independently re-fetching the same source and re-running the
comparison before consensus is reached.

## Why GenLayer

- **AI judgement is the core value**: deciding whether two pieces of
  natural-language text are meaningfully similar — beyond exact
  string matching — is exactly the kind of nuanced task a
  deterministic smart contract cannot perform.
- **Web-aware verification**: the contract fetches the comparison
  source itself inside the non-deterministic execution flow, rather
  than trusting a "similarity report" typed in by whoever calls the
  contract.
- **Consensus, not a single model call**: each validator
  independently re-fetches the same source and re-runs the judgement,
  then must agree with the leader on the exact verdict — enforcing
  multi-model agreement (GPT, Gemini, Claude, Mistral, Minimax) as a
  natural defense against any single model's bias.

## Live Demo

Contract deployed on GenLayer Studio:
[https://explorer-studio.genlayer.com/address/0x94d073617455F440539b2EF3353B4712B5F83B8a](https://explorer-studio.genlayer.com/address/0x94d073617455F440539b2EF3353B4712B5F83B8a)

## Contract Details

| Field | Value |
|---|---|
| Network | GenLayer Studio (Studionet) |
| Contract address | `0x94d073617455F440539b2EF3353B4712B5F83B8a` |
| Explorer link | https://explorer-studio.genlayer.com/address/0x94d073617455F440539b2EF3353B4712B5F83B8a |
| Deployed | Sep 19, 2026 |
| Transactions | 7 finalized (100% success rate) |

## Tech Stack

- **GenLayer Intelligent Contract** — Python contract
  (`content_registry.py`)
- **Storage** — `TreeMap[str, str]` (single map, pipe-delimited
  records for state stability)
- **AI Validators** — Multi-model router (GPT, Gemini, Claude Sonnet,
  Mistral, Minimax) via `gl.nondet.exec_prompt`
- **Web Access** — `gl.nondet.web.get` for source fetching
- **Consensus** — `gl.vm.run_nondet_unsafe` with exact-match
  validator function

## How It Works

1. **Register** — Anyone calls `register_content(content_id,
   content_text, source_url)` to register a piece of content with a
   comparison source URL. The first caller of a `content_id` becomes
   its owner; only the owner may update or re-verify.
2. **Verify** — The owner calls `verify_originality(content_id)`,
   which triggers the leader/validator consensus flow:
   - The **leader** fetches the source URL itself
     (`gl.nondet.web.get`) and asks an LLM to compare the registered
     content strictly against the fetched evidence.
   - Each **validator** independently fetches the same URL and
     independently queries the model, then compares only the
     `STATUS|SCORE` verdict against the leader's result — not the
     wording of any reasoning, since independent LLM calls may phrase
     things differently even when they agree on the outcome.
   - To make exact-match consensus reliable, the LLM is constrained
     to output only `STATUS|SCORE` (e.g. `PLAGIARIZED|90`) with no
     free-form text.
3. **Save** — The owner calls `save_verification_result(content_id,
   result)` with the exact string returned by `verify_originality`.
   The verdict is written on-chain along with a generated reason.
4. **Query** — Anyone can read the final record via `get_content`,
   `is_original`, and `get_similarity_score`.

> **Why two transactions?**
> `verify_originality` only returns the AI verdict — it does not
> persist state. Persistence happens in a separate deterministic
> write. This split avoids GenVM state rollback after long
> non-deterministic executions and guarantees 100% state persistence.

### Verdict categories

- **ORIGINAL** — similarity < 20%, content appears unique
- **DERIVATIVE** — similarity 20–70%, content is partially derived
- **PLAGIARIZED** — similarity > 70%, content is copied
- **ERROR** — verification could not be completed

### Verdict format

```text
STATUS|SCORE
```

Example:
```text
PLAGIARIZED|90
ORIGINAL|0
DERIVATIVE|45
```

### Contract methods

**Write**
- `register_content(content_id: str, content_text: str, source_url: str)` —
  register new content or update existing (owner only)
- `verify_originality(content_id: str) → str` — run AI verification
  against the source URL; returns `"STATUS|SCORE"`; does **not** persist
- `save_verification_result(content_id: str, result: str)` — persist
  the verdict returned by `verify_originality` (owner only)

**Read**
- `get_content(content_id: str) → str` — full record: status, score,
  reason, source, owner
- `is_original(content_id: str) → bool` — `true` if verdict is
  `ORIGINAL`
- `get_similarity_score(content_id: str) → int` — similarity score
  (0–100)

## How to Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/content-originality-registry
cd content-originality-registry

# 2. Open GenLayer Studio and load content_registry.py
# 3. Deploy the contract (no constructor args needed)

# 4. Register content:
#    register_content(
#      content_id:   "my-article-001",
#      content_text: "<your content, min 50 chars>",
#      source_url:   "https://en.wikipedia.org/wiki/Your_Topic"
#    )

# 5. Verify originality:
#    verify_originality(content_id: "my-article-001")
#    → Copy the returned string, e.g. "PLAGIARIZED|90"

# 6. Save the result:
#    save_verification_result(
#      content_id: "my-article-001",
#      result:     "PLAGIARIZED|90"
#    )

# 7. Query:
#    get_content(content_id: "my-article-001")
#    is_original(content_id: "my-article-001")
#    get_similarity_score(content_id: "my-article-001")
```

## Live Instance

The deployed contract at
`0x429327f11412A90cD9DC4f3A43859C614D2cC7d8` has been tested with two
verdicts:

| content_id | source_url | Verdict |
|---|---|---|
| `wiki-geografi-01` | `https://id.wikipedia.org/wiki/Geografi` | **`PLAGIARIZED` \| 90** |
| `karya-orisinal-01` | `https://id.wikipedia.org/wiki/Pantai_Parangtritis` | **`ORIGINAL` \| 0** |

Both records are persisted on-chain and queryable via the read
methods.

## Demo Evidence (from development testing)

Two-sided validation proving the AI judges in both directions:

- **Plagiarism case**
  - Content: Wikipedia's "Geografi" article excerpt
  - Source: `https://id.wikipedia.org/wiki/Geografi` →
    **`PLAGIARIZED|90`** (consensus: Accepted)
  - Reason on-chain: *Content is heavily copied from the external
    source.*
- **Originality case**
  - Content: Original short fiction about a fisherman at
    Parangtritis beach (not published anywhere)
  - Source: `https://id.wikipedia.org/wiki/Pantai_Parangtritis` →
    **`ORIGINAL|0`** (consensus: Accepted)
  - Reason on-chain: *Content appears unique. No significant matches
    found.*

Both tests achieved full consensus across the validator set with
majority `Agree` votes.

## Known Limitations

- Sources protected by anti-bot measures (Cloudflare challenges,
  JavaScript-heavy SPAs) may fail to fetch. Publicly accessible,
  text-based pages (Wikipedia, most news sites, raw GitHub) work
  reliably.
- If a source's content changes between the leader's and a
  validator's fetch (e.g. live-updating pages), validators may
  disagree even on a clear case — static reference pages are more
  reliable than dynamic content.
- `register_content` currently has no caller restriction — the first
  caller of a `content_id` becomes its owner. This is an intentional
  "first-claim" design; it does not require pre-registration or
  gating.
- Only one source URL is supported per verification. Multi-source
  comparison is planned but not yet implemented.
- Content is compared against a single external source chosen by the
  registrant — resolution quality depends heavily on which source is
  supplied.
- No dispute/appeal mechanism if a verdict is considered incorrect
  after the fact — the saved verdict is final once written.
- The two-step flow (`verify_originality` then
  `save_verification_result`) requires the caller to copy-paste the
  returned verdict — a deliberate design choice to work around a
  known GenVM state-rollback behavior on long non-deterministic
  executions.

## Future Roadmap

- **Bounty System** — reward the first valid reporter of plagiarism
- **NFT Certificate** — mint proof-of-authorship for `ORIGINAL` content
- **Multi-Source Comparison** — verify against multiple URLs
  simultaneously instead of one
- **Appeal Mechanism** — allow owners to dispute verdicts with
  additional evidence
- **Reputation Score** — track wallet reputation based on verified
  submissions
- **Single-transaction flow** — once GenVM stabilizes, merge
  verification and persistence into one call

## Security Notes

- All state changes (`records[content_id]`) occur strictly in the
  deterministic write path, **after** the leader/validator
  non-deterministic consensus completes — no writes are reachable
  from inside the AI evaluation itself.
- The model's response is parsed strictly: only the first
  `STATUS|SCORE` pattern is accepted, status is validated against the
  four allowed categories, and the score is clamped to 0–100.
  Malformed outputs become `ERROR|0` rather than silently accepted.
- Evidence is fetched by the contract itself from the caller-supplied
  URL, not accepted as free-form text — this prevents a caller from
  fabricating "evidence" to manipulate the outcome directly.
- The prompt explicitly warns the LLM that the scraped source is
  **untrusted data**, defending against prompt-injection attempts
  embedded in the source page.
- Content is truncated to 3,000 chars and evidence to 6,000 chars
  before prompting, ensuring deterministic behavior across
  validators.
- Owner gating prevents anyone other than the original registrant
  from updating or re-verifying a `content_id`.

## License

MIT — free to use, modify, and distribute.

---

*Built with GenLayer Intelligent Contracts.*
