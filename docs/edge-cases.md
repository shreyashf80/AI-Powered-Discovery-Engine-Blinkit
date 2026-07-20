# Edge Cases & Failure Scenarios

> Derived from [architecture.md](file:///Users/shreyash/NextLeap/NL%20Grad%20Project/docs/architecture.md) and [implementation-plan.md](file:///Users/shreyash/NextLeap/NL%20Grad%20Project/docs/implementation-plan.md)

This document catalogs edge cases, failure modes, and boundary conditions across every layer of the Discovery Engine. Each case includes the **trigger**, **expected behavior**, and **mitigation** strategy.

---

## 1. Ingestion Layer — Source Connectors

### 1.1 Play Store Connector

| # | Edge Case | Trigger | Expected Behavior | Mitigation |
|---|---|---|---|---|
| I-1 | Zero reviews returned | App ID is wrong, or `google-play-scraper` breaks due to Play Store UI change | Connector returns empty list; pipeline logs warning but does not crash | Validate app ID at startup; log `raw_ingested: 0` in `pipeline_stats` |
| I-2 | Reviews missing `timestamp` | Some Play Store reviews lack dates (very old reviews) | Set `timestamp` to `None`; skip from recency filter but still process | Handle `None` timestamps in all downstream comparisons |
| I-3 | Reviews in non-Latin scripts | Kannada, Tamil, Telugu reviews on the Blinkit app | `language_detected` set correctly; routed to translation step | `langdetect` handles these; translation via LLM preserves original in `language_original` |
| I-4 | Duplicate reviews from pagination | Scraper fetches overlapping pages | Content-hash dedup catches exact duplicates; source-ID dedup catches same review | Dedup runs in cleaning layer before any LLM calls |
| I-5 | Rate limiting / IP blocking | Railway datacenter IP is flagged by Google | Exponential backoff with jitter; after max retries, log failure and continue with partial data | Configurable max retries (default 3); partial ingestion is acceptable |
| I-6 | Review body is empty string | User left only a star rating with no text | `len(body) < 25` rule in Stage 1 filter catches this; discarded before LLM call | Still counted in `raw_ingested` for funnel transparency |

### 1.2 App Store Connector

| # | Edge Case | Trigger | Expected Behavior | Mitigation |
|---|---|---|---|---|
| I-7 | npm subprocess fails | `app-store-scraper` not installed, or Node.js missing on Railway | Connector raises a clear error with install instructions; pipeline continues without App Store data | Dockerfile must include Node.js; test in Phase 0 scaffolding |
| I-8 | App Store returns RSS feed errors | Apple changes RSS feed format or rate-limits | Fallback: try scraper first, then RSS; if both fail, log and skip | Multiple fetch strategies per connector |
| I-9 | Mixed-language reviews (e.g., English + Hindi in one review) | Common for Indian users to code-switch mid-review | Treat as Hinglish/code-mixed; entire review goes through LLM translation | `langdetect` may flag as `hi` or `en` — either way, pass to translation step if mixed signals |
| I-10 | App ID mismatch across regions | Blinkit may have different App Store IDs per country | Hardcode the India App Store ID; document if other regions are needed | Config-driven app ID |

### 1.3 Reddit Connector

| # | Edge Case | Trigger | Expected Behavior | Mitigation |
|---|---|---|---|---|
| I-11 | Post matches both query sets | A post about "Blinkit vs Zepto quick commerce" matches branded (Arctic Shift) AND broadened (PullPush) queries | Stored **once** with `query_tags: ["blinkit", "quick-commerce"]` — not duplicated | Dedup by `reddit:{post_or_comment_id}` before insert; merge `query_tags` |
| I-12 | Deleted / removed posts | Archive mirrors still store `[removed]` or `[deleted]` post bodies | Skip items where `body` is `[removed]`, `[deleted]`, or empty | Pre-filter in connector before returning `RawItem` |
| I-13 | Arctic Shift rate limit | Hitting ~120,000 req/hr limit (unlikely but possible with aggressive pagination) | Back off and retry; if persistent, fall back to PullPush for remaining queries | BAScraper handles rate limiting internally; add logging when throttled |
| I-14 | Arctic Shift is completely down | Server error, maintenance, or volunteer project goes offline | **All subreddit-scoped queries fall back to PullPush** — PullPush can search by subreddit too, just less efficiently | Mandatory fallback path; log which service handled each query |
| I-15 | PullPush is completely down | Server error or maintenance | **All Reddit-wide queries fall back to Arctic Shift** — run them as per-subreddit queries across the configured subreddit list (slower but functional) | Mandatory fallback path; accept reduced coverage for broadened queries |
| I-16 | **Both mirrors unreachable simultaneously** | Both volunteer services down at the same time | Pipeline **fails gracefully for Reddit only**: logs a clear error, reports `raw_ingested: 0` for Reddit in `pipeline_stats` (FR12), and continues with other sources | Pipeline does NOT silently proceed as if Reddit data were included — the funnel report shows the gap |
| I-17 | Stale / lagging archive coverage | Arctic Shift and PullPush are archive mirrors, not live Reddit — very recent posts (last few hours/days) may not yet be indexed | Accept a coverage gap for the most recent threads; posts from 1+ week ago are reliably available | Document in the pipeline report that Reddit coverage may lag 1-7 days for the newest content |
| I-18 | Post has zero comments | An upvoted post with no comments yet | Still ingest the post body itself — the post text is valid signal | `content_type: "post"` for the post, separate from comments |
| I-18a | Irrelevant subreddit results | Query `"blinkit"` on `r/india` returns posts about a different topic | Stage 1 + Stage 2 filters catch non-Blinkit content | Relevance filter is the designed safety net for noisy search results |
| I-18b | Arctic Shift `title`/`selftext` keyword search misses body-only mentions | Arctic Shift keyword search on `/api/posts/search` requires `subreddit` param and only searches `title`/`selftext` fields | Some posts mentioning Blinkit only in comments (not title) may be missed by Arctic Shift | PullPush Reddit-wide search catches body mentions; also fetch comments for discovered posts via `/api/comments/search` |
| I-18c | Different response schemas between Arctic Shift and PullPush | Field names and nesting may differ between the two services | Connector must normalize both response formats to the same `RawItem` schema | Write a dedicated response normalizer per service; test with real responses during Phase 2 |

### 1.4 YouTube Connector

| # | Edge Case | Trigger | Expected Behavior | Mitigation |
|---|---|---|---|---|
| I-19 | Quota exhausted (10,000 units/day) | Too many API calls in a single pipeline run | Stop YouTube ingestion gracefully; log how many items were fetched before quota hit | Track quota usage; prioritize comment fetching over search calls |
| I-20 | Video has comments disabled | Creator disabled comments on a Blinkit review video | `commentThreads.list` returns empty; skip to next video | Handle empty response without error |
| I-21 | Comment is a reply to a reply | YouTube comment threads have top-level + replies | Fetch top-level comments and direct replies; assign `parent_id` for replies | Map YouTube's `parentId` to our `parent_id` field |
| I-22 | Video is age-restricted or region-locked | Video metadata accessible but comments aren't | Log and skip; don't crash | Catch `HttpError` with 403 status per-video |
| I-23 | Search returns irrelevant videos | Searching "blinkit" returns unrelated results | Only fetch comments from videos whose title/description mentions Blinkit/quick-commerce | Pre-filter videos by title keyword match before fetching comments |
| I-24 | Comments in Hinglish/regional languages | YouTube comments on Indian content are heavily code-mixed | Same as I-9 — route through translation step | Handled by cleaning layer |
| I-25 | Comment contains only emojis or URLs | `"🔥🔥🔥"` or just a link | `len(body) < 25` after stripping emojis/URLs → Stage 1 discards | Strip non-text content before length check |

---

## 2. Cleaning Layer

| # | Edge Case | Trigger | Expected Behavior | Mitigation |
|---|---|---|---|---|
| C-1 | Cross-source exact duplicate | Same review text posted on both Play Store and Reddit | SHA-256 content hash matches; keep the first-seen copy, drop the duplicate | Content-hash dedup runs across all sources |
| C-2 | Near-duplicate but not exact | Same user writes slightly different reviews on Play Store vs App Store | Content-hash won't catch this; both are kept and independently tagged | Acceptable — LLM may tag them differently based on nuance; funnel stats reflect both |
| C-3 | `langdetect` misclassifies language | Short Hinglish text detected as `en` instead of `hi` | Translation step is skipped; LLM extraction may still work (Groq/Gemini handle Hinglish) | For short text, consider running translation regardless if source is Indian |
| C-4 | Translation LLM call fails | Groq + Gemini both rate-limited during translation batch | Keep original untranslated text; mark `language_original` = body; proceed to extraction | LLM extraction models handle Hinglish reasonably even without explicit translation |
| C-5 | Spam bot with unique content | Bot posts unique-looking promotional text each time | Content-hash dedup won't catch it; spam filter needs to detect promotional patterns (URLs, repeated CTAs) | Pattern-match on promotional indicators: affiliate links, "use code", "download now" |
| C-6 | Legitimate review contains a URL | User links to a screenshot or product page | Don't strip the URL from body; only flag as spam if the *entire* content is a URL with no other text | Spam filter checks: is the item *predominantly* a link, or does it have substantive text alongside? |
| C-7 | Body is HTML-encoded | Scraper returns `&amp;`, `&lt;`, etc. | Decode HTML entities before hashing and processing | Run `html.unescape()` as first step in cleaner |

---

## 3. Relevance Filter (Stage 1)

| # | Edge Case | Trigger | Expected Behavior | Mitigation |
|---|---|---|---|---|
| F-1 | Short but signal-rich review | `"Blinkit milk always expired"` (27 chars, has category keyword "milk") | **Pass through** — has category keyword despite being short | Length check is `len < 25 AND no keyword`, not just `len < 25` |
| F-2 | Delivery complaint with category mention | `"Won't order meat from Blinkit, delivery is too slow for perishables"` | **Pass through** — legitimate `barrier_type` signal tied to a category | Delivery complaints are NOT blanket-discarded; only discarded if no category/behavior signal |
| F-3 | Pure app crash report | `"App keeps crashing after latest update, can't even open it"` | **Discard** — all tokens are `APP_TECHNICAL_VOCAB`, zero `BEHAVIOR_SIGNAL_WORDS` | Stage 1 rule 2 catches this |
| F-4 | App crash + category mention | `"App crashes every time I try to order electronics"` | **Pass through** — has category keyword "electronics" alongside technical vocab | Category keyword presence overrides the pure-technical discard rule |
| F-5 | Review is exactly 25 characters | `"Good app for groceries!!"` (exactly 25 chars) | **Pass through** — threshold is `< 25`, not `<= 25` | Boundary condition: use strict `<` comparison |
| F-6 | Review in non-English without category keywords | Hindi review about dairy products — no English keyword match | Stage 1 passes it through (ambiguous); Stage 2 LLM handles Hindi | Category keyword list should include transliterated Hindi terms if feasible, otherwise rely on LLM |
| F-7 | False positive discard — review about trust/quality but no category keyword | `"I just don't trust the quality of products on Blinkit"` | **Pass through** — contains `BEHAVIOR_SIGNAL_WORDS` ("trust", "quality") | Rule 2 only discards if ONLY tech vocab AND NO behavior signals |
| F-8 | Emoji-heavy review with category signal | `"🥛 Blinkit dairy 👍👍👍"` | After emoji stripping, check for category keyword "dairy" → pass through | Strip emojis before keyword matching, not before body storage |

---

## 4. Extraction Layer (Stage 2 — LLM)

| # | Edge Case | Trigger | Expected Behavior | Mitigation |
|---|---|---|---|---|
| E-1 | LLM returns invalid JSON | Groq returns markdown-wrapped JSON or malformed output | Parse attempt fails; retry once with a stronger "return ONLY valid JSON" prompt | Regex-strip markdown fences (````json...````) before parsing; retry with explicit format instructions |
| E-2 | LLM hallucinates a category | LLM outputs `"category_mentioned": ["Toys & Games"]` — not in canonical list | Pydantic validation rejects non-canonical category | Enum validation against `CORE_CATEGORIES ∪ EXPLORATORY_CATEGORIES`; reject or map to `"other"` |
| E-3 | LLM sets multiple behavior_types | Review describes both `habit` and `abandoned-attempt` | Schema allows only one value | Prompt instructs: "pick the dominant behavior_type"; if LLM returns a list, take the first |
| E-4 | Groq rate-limited, Gemini also rate-limited | Both free tiers exhausted simultaneously | Log failure; skip this item; increment a `failed_extraction` counter in pipeline stats | After 3 retries on both providers, mark item as `extraction_failed` and continue |
| E-5 | LLM marks everything as `relevant: false` | Prompt is too strict; taxonomy wording causes over-filtering | Funnel stats show `relevant_embedded: 0` — no data to query | **Dry-run gate catches this** — check before scaling; adjust prompt/taxonomy |
| E-6 | LLM marks everything as `relevant: true` | Prompt is too lenient | Storage bloats; many irrelevant items embedded | Dry-run gate: manually inspect tagged output; tighten relevance criteria in prompt |
| E-7 | Review mentions multiple categories | `"I buy milk and electronics from Blinkit"` | `category_mentioned: ["Dairy & Bakery", "Electronics & Accessories"]` — list is valid | Schema supports list of categories; both get `category_tier` labels |
| E-8 | LLM returns empty `source_snippet` | LLM doesn't extract a representative excerpt | Use full `body` as fallback snippet; log warning | If `source_snippet` is empty/null, fall back to first 200 chars of `body` |
| E-9 | Item body exceeds LLM context window | A very long Reddit post (>10,000 tokens) | Truncate to first N tokens before sending to LLM | Pre-truncate at ~3,000 tokens per item (well within 131K Groq context, but keeps costs low) |
| E-10 | Concurrent extraction hits rate limits | 5 concurrent requests all trigger Groq rate limiting simultaneously | All 5 fall back to Gemini; Gemini may also rate-limit | Semaphore-controlled concurrency; per-provider rate tracking; dynamic concurrency reduction on rate-limit signals |
| E-11 | LLM response is in a different language | Groq/Gemini responds in Hindi to a Hindi input | Parse fails if field names are translated | System prompt explicitly states: "Always respond in English. Field names must match the schema exactly." |

---

## 5. Embedding & Vector Store

| # | Edge Case | Trigger | Expected Behavior | Mitigation |
|---|---|---|---|---|
| V-1 | ChromaDB collection already exists | Pipeline re-run after a previous successful run | `get_or_create_collection()` — don't error on existing collection | Use ChromaDB's `get_or_create_collection` API |
| V-2 | Duplicate embedding on re-run | Same item embedded twice across two pipeline runs | ChromaDB uses item `id` as document ID; second insert is an upsert | Use `collection.upsert()` instead of `collection.add()` |
| V-3 | `source_snippet` is very short | LLM returned a 5-word snippet | Embedding quality is lower for very short text; retrieval may be imprecise | Acceptable trade-off; full `body` is stored in `tagged_items` for synthesis context |
| V-4 | Embedding model OOM on Railway | `all-MiniLM-L6-v2` (~80MB) + ChromaDB + SQLite exceed Railway free memory | Process crashes | Embed in batches (batch size ~100); free model from memory between pipeline stages if needed |
| V-5 | ChromaDB persist directory missing | First run, `/data/chroma/` doesn't exist yet | ChromaDB creates directory on first use | Ensure `DATA_DIR` exists at startup; `os.makedirs(exist_ok=True)` |
| V-6 | Railway volume not mounted | Deployment config error — `/data` is ephemeral | Data lost on redeploy; ChromaDB and SQLite reset | Startup health check: verify `/data` is a mount point; log critical warning if not |
| V-7 | Metadata field too long for ChromaDB | A `category_mentioned` list with many categories serialized as string | ChromaDB has metadata value size limits | Serialize lists as JSON strings; truncate if needed |

---

## 6. RAG Chat Layer

| # | Edge Case | Trigger | Expected Behavior | Mitigation |
|---|---|---|---|---|
| R-1 | Question is completely off-topic | User asks: "What's the weather today?" | No relevant chunks retrieved; LLM should respond: "I don't have information about that. I can answer questions about Blinkit user behavior." | Retrieval returns low-similarity results → if max similarity < threshold, return a canned "no relevant data" response |
| R-2 | Question is ambiguous | "Tell me about categories" — which aspect? | Retrieve broadly; LLM synthesis covers multiple angles | Acceptable — broad retrieval + LLM contextualizes |
| R-3 | Zero vectors in ChromaDB | Pipeline hasn't run yet, or all items were `relevant: false` | Chat should return: "No data available. Please run the ingestion pipeline first." | Check `collection.count()` before retrieval; return early with helpful message |
| R-4 | Retrieved chunks contradict each other | 5 reviews say "Blinkit electronics are great", 3 say "never trust Blinkit for electronics" | Synthesis prompt must present both sides with frequency: "5 of 8 reviews say…" (FR13) | Explicit prompt instruction: "When evidence splits, present both sides with counts" |
| R-5 | All retrieved chunks are from one source | Question about a niche topic only discussed on Reddit | Answer cites only Reddit; source breakdown shows 100% Reddit | Acceptable — show source breakdown transparently so user knows coverage is thin |
| R-6 | User sends empty question | Frontend submits `question: ""` | API returns 422 validation error | Pydantic model: `question: str` with `min_length=1` validator |
| R-7 | User sends extremely long question | 10,000-character question | Truncate question to reasonable limit before retrieval and synthesis | Max question length: 1,000 chars; return 422 if exceeded |
| R-8 | Filter combination returns zero results | `category_tier: "exploratory"` + `source: "youtube"` — no YouTube items about exploratory categories | Return: "No results match these filters. Try broadening your search." | Check result count after filtering; return helpful empty-state message |
| R-9 | Synthesis LLM fails | Both Groq and Gemini error during synthesis | Return 503 with: "Unable to generate answer. Please try again." | Don't return partial/garbage answers; clean error response |
| R-10 | Synthesis takes too long | LLM inference >30 seconds | Frontend shows timeout; user retries | Set HTTP timeout at 60s; show loading state in frontend; suggest retry on timeout |

---

## 7. Insight Summary Generator

| # | Edge Case | Trigger | Expected Behavior | Mitigation |
|---|---|---|---|---|
| S-1 | One seed question returns zero citations | Not enough data about "elderly/senior" users | Summary notes: "Insufficient data to answer this question. Only N items mentioned elderly users." | Include confidence level and sample size per question |
| S-2 | Summary generation takes very long | 8 sequential RAG queries × LLM synthesis time | Could exceed 2+ minutes | Show progress indicator in frontend; consider parallel execution of independent questions |
| S-3 | Emergent theme detection fails | LLM can't find themes beyond the 8 seed questions | `emergent_themes: []` — empty list | Acceptable; note "No additional themes detected beyond the seed questions" |
| S-4 | Same citation appears in multiple answers | A rich review is relevant to multiple seed questions | Same snippet cited 3+ times across different answers | Acceptable — deduplicate citations in the final report display if needed |

---

## 8. API Layer

| # | Edge Case | Trigger | Expected Behavior | Mitigation |
|---|---|---|---|---|
| A-1 | Invalid `ADMIN_SECRET` on ingest endpoint | Attacker or misconfigured client | Return 401 Unauthorized; log the attempt | Compare `Authorization: Bearer <token>` against env var; constant-time comparison |
| A-2 | Concurrent ingest triggers | Admin triggers pipeline while another run is in progress | Return 409 Conflict: "Pipeline already running (run_id: ...)" | Track `is_running` state; prevent concurrent pipeline executions |
| A-3 | Pipeline crashes mid-run | OOM, network error, or unhandled exception | `pipeline_stats` may be incomplete; raw items may be partially ingested | Wrap pipeline in try/catch; write partial stats on failure; mark run as `status: "failed"` |
| A-4 | CORS preflight fails | Frontend domain not in allowed origins | Browser blocks the request; frontend shows network error | Set CORS origins to exact Vercel domain; include `localhost:3000` for dev |
| A-5 | Railway free tier hours exhausted | 500 hours/month used up | Backend goes offline; frontend shows connection errors | Monitor usage via Railway dashboard; optimize: don't leave the service running idle |
| A-6 | Request body exceeds size limit | Malformed or malicious large POST payload | FastAPI/Uvicorn returns 413 | Set `--limit-max-request-size` in Uvicorn config |

---

## 9. Frontend

| # | Edge Case | Trigger | Expected Behavior | Mitigation |
|---|---|---|---|---|
| FE-1 | Backend is unreachable | Railway is down, or `NEXT_PUBLIC_API_URL` is wrong | Show: "Unable to connect to the server. Please try again later." | Wrap all API calls in try/catch; show user-friendly error states |
| FE-2 | Answer contains no citations | LLM synthesized without citing sources (prompt failure) | Show answer but flag: "⚠️ No source citations available for this answer" | Frontend checks `citations.length === 0` and shows warning |
| FE-3 | Citation URL is null | Source item had no permalink (e.g., scraped forum post) | Show citation badge without link; no broken link | Conditionally render link only if `url !== null` |
| FE-4 | Very long answer text | LLM generates 2,000+ word answer | Scroll within answer container; don't break layout | CSS: `overflow-y: auto; max-height: ...` on answer container |
| FE-5 | Rapid-fire questions | User sends 5 questions in 2 seconds | Queue or debounce; don't fire 5 parallel API calls | Disable send button while request is pending; debounce input |
| FE-6 | Special characters in question | User types `<script>alert('xss')</script>` | No XSS — React escapes HTML by default; question sent as plain text to API | React's JSX auto-escaping + API treats question as plain string |
| FE-7 | Mobile viewport | User opens chat UI on phone | Layout should be responsive; no horizontal overflow | TailwindCSS responsive classes; test at 375px viewport width |

---

## 10. Data Integrity & Storage

| # | Edge Case | Trigger | Expected Behavior | Mitigation |
|---|---|---|---|---|
| D-1 | SQLite file corruption | Crash during write; Railway volume issue | Pipeline can't start; queries fail | Startup health check: try a simple query; if corrupt, log critical error and alert |
| D-2 | Pipeline stats don't add up | `raw_ingested ≠ stage1_passed + stage1_discarded` | Funnel report shows inconsistent numbers | Compute all stats within a single transaction; assert consistency before commit |
| D-3 | Deletion of irrelevant items fails | SQLite lock or error during `DELETE FROM raw_items WHERE relevant = false` | Irrelevant items persist; storage grows | Retry deletion; if persistent failure, log warning — storage bloat is inconvenient but not fatal |
| D-4 | Re-running pipeline doubles data | Running `ingest` twice without clearing | Connector-level dedup (by source ID) prevents duplicate raw items; embedder uses `upsert` | Dedup at every stage: connector (source ID), cleaner (content hash), embedder (document ID) |
| D-5 | Storage exceeds Railway free-tier limits | More data than estimated (~60MB) | Volume full; writes fail | Monitor storage via `/api/stats` (reports `storage_used_mb`); pipeline checks space before starting |

---

## 11. LLM Provider Edge Cases

| # | Edge Case | Trigger | Expected Behavior | Mitigation |
|---|---|---|---|---|
| L-1 | Groq model deprecated | Groq sunsets `llama-3.3-70b-versatile` | API returns model-not-found error | Config-driven model name; easy to swap; fallback to Gemini continues working |
| L-2 | Gemini safety filter blocks response | Gemini flags a review as unsafe content | Returns empty or filtered response | Catch safety-filter responses; retry with modified prompt or skip item |
| L-3 | API key revoked or expired | Key rotation, billing issue, or abuse detection | All LLM calls fail | Clear error logging; pipeline halts with "check API keys" message |
| L-4 | Token count mismatch | Estimated tokens ≠ actual; input longer than expected | Groq rejects with context-length error | Pre-estimate token count; truncate if approaching limit (131K for Groq, 1M for Gemini) |
| L-5 | Different JSON structure between providers | Groq and Gemini format JSON responses slightly differently | Parsing works for one but fails for the other | Normalize JSON parsing: strip whitespace, handle both `true`/`True`, use Pydantic's lenient parsing |
| L-6 | Free tier terms change | Provider reduces free quota or adds restrictions | Pipeline throughput drops or stops | Monitor provider changelogs; architecture supports swapping providers via config |

---

## Summary: Critical Edge Cases to Test During Dry-Run

> [!IMPORTANT]
> These are the highest-risk edge cases that must be validated during the Phase 3 dry-run gate:

| Priority | Edge Case IDs | What to Check |
|---|---|---|
| 🔴 Critical | E-1, E-2, E-5, E-6 | LLM output quality: valid JSON, canonical categories, balanced relevance |
| 🔴 Critical | I-11, I-16, D-4 | Deduplication: Reddit dual-query across two mirrors, both-mirrors-down graceful failure, re-run safety |
| 🔴 Critical | I-14, I-15, I-18c | Reddit mirror fallback: Arctic Shift→PullPush and vice versa, response schema normalization |
| 🟠 High | F-1, F-2, F-3, F-4 | Filter rules: signal-rich short reviews, delivery+category, pure-tech |
| 🟠 High | L-1, L-5, E-4 | LLM fallback: Groq→Gemini, both-down handling, JSON normalization |
| 🟡 Medium | I-17 | Reddit mirror data staleness: very recent posts may not be indexed |
| 🟡 Medium | V-6, D-1 | Storage: Railway volume mounted, SQLite integrity |
| 🟡 Medium | R-1, R-4 | RAG: off-topic handling, contradictory evidence presentation |
