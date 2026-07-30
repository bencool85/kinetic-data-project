# Business Context — Kinetic

An on-demand fitness content platform (app + web). No proprietary hardware
(unlike Peloton) — revenue comes from three lines:

## 1. Subscription
- **Kinetic Basic** — $19.99/mo or $179/yr (~25% off annual)
- **Kinetic Plus** — $34.99/mo — adds live classes, monthly 1:1 coaching credit,
  early access to new programs
- **7-day free trial** before first billing on all plans
- Subscribers get the **entire course catalog included** — they do not need, and
  essentially never buy, a la carte courses
- Subscribers get a **discount on merch** (member price)

## 2. A la carte training courses
- Effectively a **non-subscriber-only** behavior — the way to access content without
  committing to a subscription
- Categories: Strength, Yoga, Running, Cycling, HIIT, Mobility & Recovery, Nutrition
  Coaching
- Pricing: single class ~$9.99, multi-week programs $79–$149
- Purchasing a course **requires an account** (customer_id) — you need to log in to
  watch what you bought, so there is no such thing as a guest course purchase

## 3. Merch & gear
- Apparel (leggings, tops, jackets), accessories (bottles, bags, headbands), light
  equipment (mats, resistance bands, foam rollers), tech accessories (HR straps, phone
  mounts)
- **Guest checkout is valid here** — physical goods can be shipped without an account
- Subscribers get a discount

## Deliberately excluded for simplicity
- No gifting / gift subscriptions — every purchase is for the purchaser's own account
- No proprietary hardware/equipment sales
- No customer support, reviews, or loyalty/referral program

## Customer personas (source material for the `segments` table)
- Active subscribers (Basic / Plus)
- Free-trial users (converted / expired / canceled during trial)
- Lapsed/churned subscribers, some who later win back
- Course-only buyers who never subscribe
- Merch-only one-time buyers (often guest checkout)
- VIP/power users (high engagement, high LTV)
- Cart abandoners / website visitors who never convert (anonymous-grain segments)

## Seasonality calendar (drives signups, ad spend, and traffic together)
- **January** — New Year's resolution surge, biggest acquisition month
- **Summer (Jun–Aug)** — "shred season," running/outdoor content emphasis
- **November** — Black Friday/Cyber Monday, merch + annual-plan discounting spikes
- **December** — gifting season for merch specifically (not gift subscriptions)
- Underlying 3-year growth trend layered on top of the above
