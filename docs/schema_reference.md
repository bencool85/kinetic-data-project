# Schema Reference — 47 Tables

Raw, source-system-shaped tables (no pre-built dim/fact mart layer). Scale: 100
customers, 3 years of history (Aug 2023 – Jul 2026), delivered as CSVs with
intentional realistic messiness (guest checkouts, failed payments, missing UTMs,
duplicate webhook-style events, etc.).

## Identity & Account
- `customers` — customer_id, email, name, created_at, **signup_source** (derived from
  true simulated first touch), email/push opt-ins, is_deleted
- `customer_addresses`
- `devices` — device_id, customer_id (nullable — devices can be anonymous)
- `identity_map` — anonymous_id → customer_id resolution events (populated at
  login/signup, never retroactively)

## Product Catalog
- `products` — merch + course items, category, is_subscription_eligible
- `product_variants`
- `subscription_plans` — Basic/Plus, billing_interval, price (not tied to specific
  products — subscription = full catalog access)

## Commerce (storefront only — merch + course, NOT subscription billing)
- `orders` — order_type = **'merch' or 'course' only**. Guest checkout (null
  customer_id + guest_email) valid **only** for order_type='merch'. order_type='course'
  always has a customer_id.
- `order_line_items`, `payments`, `refunds`, `discount_codes`

## Subscriptions (Stripe-shaped billing, fully separate from storefront)
- `subscriptions` — status intervals (trialing/active/paused/canceled/past_due)
- `subscription_events` — trial_started, trial_converted, trial_expired,
  canceled_during_trial, renewed, upgraded, downgraded, payment_failed, canceled,
  resumed
- `invoices`

**Business rule:** no `orders` row with order_type='course' may fall within a period
where the same customer had an active subscription interval in `subscriptions`.

## Audience & Segmentation
- `segments` — one dimension table, two grains distinguished by `audience_grain`
  ('customer' | 'anonymous_device'). Anonymous rows populate `ad_platform` and
  `platform_audience_id` (the custom-audience ID assigned by that platform);
  customer-grain rows populate `source_system` instead.
- `customer_segment_membership` — effective-dated (entered_at/exited_at), **customer
  grain only** — anonymous segments never get rows here. Membership is computed from
  actual behavior in the timeline, not invented independently.
- Each paid-media platform's ad-set-level table gets a nullable `targeting_segment_id`
  → `segments.segment_id`, representing retargeting/custom-audience targeting.

## Paid Media — 6 platforms, API-accurate field names
- **Meta**: `meta_campaigns`, `meta_ads`, `meta_ad_insights_daily`,
  `meta_ad_actions_daily` (normalized `actions` array — action_type/value per row)
- **Google Search**: `google_search_campaigns`, `google_search_ad_groups`,
  `google_search_performance_daily` (cost in micros), `google_search_keyword_performance_daily`
  (includes quality_score)
- **YouTube** (Google Ads, VIDEO channel type): `youtube_campaigns`, `youtube_ad_groups`,
  `youtube_performance_daily` (video_views, video_view_rate, average_cpv)
- **Google Programmatic (DV360)**: `dv360_insertion_orders`, `dv360_line_items`,
  `dv360_performance_daily` (exchange, environment — genuinely different schema shape,
  real-time bidding across the open web)
- **Snap**: `snap_campaigns`, `snap_ad_squads`, `snap_ads`, `snap_stats_daily` (spend in
  micro currency)
- **TikTok**: `tiktok_campaigns`, `tiktok_adgroups`, `tiktok_ads`, `tiktok_reports_daily`

No user-level joins from ad platforms to our own data — attribution only via UTM
parameters on `web_sessions` (see generation_plan.md conventions).

## Email & Push (Braze-shaped, mirrored 2-table pattern per channel)
- `braze_email_campaigns`, `braze_email_events` (dot-path event_type naming, e.g.
  `users.messages.email.Send/.Open/.Click/.Bounce/.Unsubscribe`)
- `braze_push_campaigns`, `braze_push_events` (same shape, device_id/platform instead
  of email_address)
- external_user_id is (almost) always populated here — unlike web/app, Braze can't
  send to someone with no identifier

## Web Browsing
- `web_sessions` — anonymous_id always present, customer_id nullable (populated only
  once identity_map resolves it); utm_source/utm_medium/utm_campaign
- `web_events` — page_view/product_view/add_to_cart/begin_checkout/purchase/search
  (fitness-specific vocabulary to be added when we build this table)

## App Usage
- `app_sessions`, `app_events` — fitness-specific vocabulary to be added
  (workout_completed, class_started, streak_achieved, etc.)
