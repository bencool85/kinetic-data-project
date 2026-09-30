# Phase 8 pilot scope: CMO paid-media check (DRAFT, in Ben's review)

Chosen by Ben 2026-09-30. Persona: CMO / performance marketing.

## The use case in one line
"Where did our ad money go, what did each platform say it got back, and is it
getting cheaper to win a subscriber?" Answered by the agent using the Kinetic
Skill (docs/kinetic_skill.md) over `mart_paid_media_monthly` and
`mart_acquisition_efficiency_monthly`. No new models needed.

Comes from the Phase 0 Performance Marketing stories (spend and platform-reported
efficiency; CTR/CVR by platform). Platform grain only: the marts have no campaign or
ad-format level.

## Why this one first
- Runs on marts that are already built and validated, so the pilot tests the agent,
  not new data work.
- It covers the riskiest traps: platform-reported conversions (not subscribers), Meta
  has no conversion value, and CAC cannot be split by channel.

## Out of scope for this pilot
- Funnel by channel (CMO story 1): the next use case. It needs a new mart on
  `customers.signup_source`, plus Ben's call on whether signup_source counts as attribution.
- Retention by channel (CMO story 2), churn, LTV: no marts yet.
- Campaign- or ad-format-level answers.

## Test questions and the correct answers (live data, checked 2026-09-30)
"Last quarter" = Q2 2026 (Apr-Jun), the last complete quarter. Data ends 2026-07-30,
so July 2026 is a partial month and must be called out if used.

| # | Question | Correct answer (what a good reply contains) |
|---|----------|---------------------------------------------|
| 1 | How did we split ad spend across platforms last quarter? | Total $146,284. TikTok $42,057 (28.8%), Meta $34,736 (23.7%), Google Search $31,409 (21.5%), YouTube $16,732 (11.4%), DV360 $12,244 (8.4%), Snap $9,105 (6.2%). |
| 2 | Which platform was cheapest per conversion last quarter? | YouTube $21.56, then TikTok $31.94, Google Search $37.27, Snap $46.30, Meta $63.85, DV360 $89.23. Must say these are **platform-reported** conversions (Meta = purchases only), recomputed from sums. |
| 3 | Is it getting cheaper to acquire a subscriber? | Blended CAC by quarter: Q1-25 $9,268, Q2-25 $10,992, Q3-25 $7,012, Q4-25 $12,090, Q1-26 $7,007, Q2-26 $6,649 (lowest). Small counts (10-28 new subscribers a quarter), so it moves a lot. Blended only. |
| 4 | What's our CAC on TikTok? *(guardrail)* | Must decline a TikTok CAC: no key links an ad to a subscriber. Offer blended CAC and TikTok's platform-reported cost per conversion instead, clearly labelled as different things. |
| 5 | What was Meta's ROAS last quarter? *(guardrail)* | Must say it is not available: Meta reports no conversion value (null every month). May give the other platforms' reported ROAS, labelled as platform-reported. |
| 6 | Platforms say ~3,800 conversions last quarter. Why only 22 new subscribers? *(trap)* | Platform conversions are not subscribers: they include course/merch purchases, each platform counts its own (they overlap) and they can be modelled (fractional). Blended CAC uses first-time subscribers from our own data. |

## Pass criteria (playbook exit test: 3+ real questions, correct and cited)
- Numbers match the table above (to the dollar or 0.1 pt).
- Each answer names the mart it used and the `data_through` date.
- Guardrail questions (4-6) are declined or explained, never invented.
- The CMO (Ben playing the role) asks at least 3 of their own questions on top of these.

## Still to decide before running it
1. Production schema: the Skill points at `dbt_dev_marts`. Keep it for the pilot, or
   build a `prod` target first?
2. Where the Skill lives: `.claude/skills/` (Claude Code) vs claude.ai upload
   (MotherDuck connector).
3. Read-only access: the agent uses md_select.py (SELECT-only) or a read-only
   MotherDuck token/share.
4. Feedback: one line per question (right / wrong / missing caveat) in a pilot log.
