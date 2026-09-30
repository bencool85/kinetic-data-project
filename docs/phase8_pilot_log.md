# Phase 8 pilot log: CMO paid-media check

One row per question asked to the pilot agent (claude.ai + Kinetic Skill + MotherDuck connector,
read-only). Expected answers for Q1-Q6 are in docs/phase8_pilot_scope.md. Graded by Claude Code
from the reply Ben pastes in.

Verdict: RIGHT / WRONG / CAVEAT MISSED / DECLINED OK (guardrail held) / DECLINED WRONGLY.
Cited = names the mart and the data_through date.

| # | Date | Question | Agent's answer (short) | Verdict | Cited? | Notes |
|---|------|----------|------------------------|---------|--------|-------|
| 1 | 2026-09-30 | How did we split ad spend across platforms last quarter? | Q2 2026 total $146,284; TikTok $42,057 (28.8%), Meta $34,736 (23.7%), Google Search $31,409 (21.5%), YouTube $16,732 (11.4%), DV360 $12,244 (8.4%), Snap $9,105 (6.2%). Added CTR/CPC per platform. | RIGHT | Yes (mart_paid_media_monthly, Apr-Jun 2026, data through 2026-07-30) | Every number matches the scope table; the extra CTR and CPC figures recomputed from the mart sums also match (e.g. Google Search CTR 4.57%, YouTube CPC $2.52). It stated how it read "last quarter". Summary percentages (74%, about 20%, about 3x CTR) check out. Snap asterisk footnote was cut off in the screenshot: confirm it says Snap clicks are swipe-ups. |
| D1 | 2026-09-30 | (Ben's own request) Build a dashboard: https://claude.ai/artifact/Y6QwXUZ9Zh8z1yjSRbRVM8 | Static one-page dashboard, 36 months of mart results baked in: KPIs (spend, first-time subs, blended CAC, net new subs, MRR, storefront revenue), spend vs outcome chart, platform table, mix over time, subscriber and storefront charts, caveat footer. | CAVEAT MISSED (one) | Yes (footer names dbt_dev_marts marts; states data through 30 July 2026) | Checked: Q2-26 platform spend, totals 174 first-time / 199 new / 101 churned, Jul-26 MRR $2,133.07 and 98 active, Q2-26 blended CAC $6,649 all match; ratios recomputed from sums; Meta ROAS "Not reported"; conversions "Not additive"; Snap swipe-ups noted. MISS: the summary line says paid media "brought in" N first-time subscribers, which is causal and contradicts the Skill and the page's own footer (blended CAC includes organic; no ad-to-subscriber key). Suggested wording: "spend of $X alongside N first-time subscribers". Not verified: monthly discount/refund/guest shares. Data is hardcoded, not live. |
