# Conserve It — Research

> Source ad: `job-ads/conserve-it/spec.yml` (Graduate Software Developer, Niagara Applications) · Researched: 2026-05-02 · Skill version: research-company

## Layer 1 — Company

- **Identity**: IoT and building automation company developing hardware and software for smart buildings, specialising in chiller plant control and optimisation.
- **Mission / positioning**: "Revolutionising Smart Buildings" — energy-efficiency-led; the company name itself frames the brand around conservation. Real-time optimisation framed as both an engineering problem and a sustainability outcome.
- **Scale**: Privately held specialist firm, not ASX-listed. Australian. Smaller than mainstream BMS players (Honeywell, Siemens, Johnson Controls), competing on the depth of their Niagara/edge integration rather than breadth.
- **Geography**: Australian-based; international deployments via Niagara's global system-integrator channel. AU presence is core, which is favourable for a Subclass 485 candidate (Principle 3 applies — work-rights line stays on the contact block, no in-body visa narration unless the ad gates on PR; this ad does not).
- **Recent signals**: Released three new Niagara 4 applications (Telegram Connector, Utilities Module, etc.) extending PlantPRO's surrounding ecosystem. Active joint webinar with Tridium itself, indicating partner-tier status.

Sources:
- [conserveitiot.com — homepage](https://www.conserveitiot.com/)
- [conserveitiot.com — Niagara Software](https://www.conserveitiot.com/niagarasoftware)
- [conserveitiot.com — Three new applications for Niagara 4](https://www.conserveitiot.com/post/conserve-it-releases-three-new-applications-for-niagara-4)

## Layer 2 — Division

- **Name**: Niagara Applications Development team — discrete enough to have a Team Lead reporting line in the ad.
- **Charter**: Develops PlantPRO and related applications **on top of the Tridium Niagara 4 framework**. Distinct from a hypothetical "Hardware/Edge Controller" arm (the CI-J-8000, CI-534 controllers themselves) — this division writes the *software* that runs on those controllers and orchestrates with the wider Niagara supervisor network.
- **External surface**: Joint conference decks with Tridium (Chirayu Shah's Niagara-at-the-Edge talk), a public catalogue of Niagara 4 applications, and the PlantPRO product page. The division has visible technical voice through Tridium's partner channels.
- **Leadership signal**: Team Lead, Niagara Applications (named in the ad as the reporting manager; not publicly named in the ad). Chirayu Shah (GM) is the public technical voice on Tridium's stage.

Sources:
- [Tridium PDF — Conserve It Edge IoT Controllers (Chirayu Shah)](https://pages1.tridium.com/rs/808-SGM-271/images/ChirayuShah%20-%20Niagara%20at%20the%20Edge%20-%20Final.pdf)
- [Tridium PDF — Advanced Chiller Plant Control and Optimisation (NS18)](https://pages1.tridium.com/rs/808-SGM-271/images/ChirayuShah%20-%20Advanced%20Chiller%20Plant%20Control%20and%20Optimisation%20NS18%20-%20Final.pdf)

## Layer 3 — Team

- **Mission**: Ship and evolve PlantPRO + related Niagara 4 applications for chiller plant optimisation across multi-vendor deployments worldwide.
- **Lead**: Reports to "Team Lead, Niagara Applications" — title only, name not in the ad.
- **Size**: *not surfaced* — small specialist firm, so plausibly 5–15 engineers, but do not state this as fact in cover letter.
- **Working model**: *not stated explicitly in the ad*; assume hybrid Melbourne-based unless confirmed.
- **Recent team output**: The three new Niagara 4 applications (released 2024–2025) and the Tridium conference talks are the team's public output. **No public GitHub org for source** — Niagara framework code is licensed and distributed through Tridium channels, not open-source.

Sources: see Layer 2.

## Layer 4 — Project / Product

- **Name**: PlantPRO (and PlantPRO CORE) — flagship; MultiPRO is the related multi-chiller variant.
- **Shape** (the cover-letter anchor):
  - **Digital twin** of the chiller plant, replicating operations across all conditions.
  - **Real-time machine learning** to predict energy usage and capture equipment performance degradation.
  - **Real-time optimisation**: assesses operational scenarios to select the most efficient combination of equipment (load distribution, condenser water flow setpoints, etc.).
  - **Edge / on-prem deployment** on embedded Niagara controllers — *no cloud subscription required, runs without stable internet*. Latency-sensitive, availability-critical.
  - **Vendor-agnostic**: controls 1–10 chillers from any manufacturer.
- **Customer**: facility owners and integrators of large commercial buildings, data centres, hospitals, universities — anywhere with a chiller plant.
- **Constraints**:
  - On-site embedded execution → memory and CPU budgets matter; can't lean on cloud burst.
  - Live equipment → uptime and graceful degradation are non-negotiable.
  - Multi-vendor hardware → strong abstraction layer over the chiller fleet.
  - Long deployment lifetimes (years), so backwards-compat and observability matter more than rapid iteration.
- **Distinctive technical concepts** to mirror in cover letter / interview: *digital twin, real-time ML, edge deployment, vendor-agnostic abstraction, self-creating control logic, HTML5 Niagara 4 dashboards*.

Sources:
- [PlantPRO CORE — product page](https://www.conserveitiot.com/plantpro)
- [Tridium PDF — Edge IoT Controllers (Chirayu Shah)](https://pages1.tridium.com/rs/808-SGM-271/images/ChirayuShah%20-%20Niagara%20at%20the%20Edge%20-%20Final.pdf)
- [PlantPRO Booklet (older overview)](https://www.scribd.com/document/379147937/PlantPRO-Booklet2014-LITE)
- [YouTube — Introduction to Conserve It and PlantPRO](https://www.youtube.com/watch?v=Ct2jDipp530)

## Layer 5 — Tech stack

| Category | Findings | Confidence |
|---|---|---|
| Languages (essential) | Java or C++, JavaScript with React + TypeScript | confirmed (ad) |
| Application framework | **Tridium Niagara 4** (the entire team's substrate); applications run inside Niagara's runtime | confirmed |
| UI | HTML5 Niagara 4 dashboards (in-framework), React/TS for any standalone web surface | confirmed (PlantPRO/Tridium decks) |
| ML / Optimisation | Real-time ML for energy prediction and equipment-degradation detection — runs *on the controller*, not cloud | confirmed (product page) |
| Hardware | CI-J-8000, CI-534, MultiPRO, PlantPRO controllers — Niagara-based edge controllers | confirmed |
| Comms protocols | Niagara's driver suite + Modbus, RS485/RS232 (desirable in ad) — chiller and BMS protocols | likely |
| Build tooling | Gradle, Maven (desirable in ad — Java ecosystem standard) | likely |
| CI/CD | Jenkins (desirable in ad), implies on-prem build infrastructure | likely |
| VCS / collaboration | Git, Atlassian suite (Jira/Confluence) — desirable in ad | likely |
| Multi-threading | First-class concern (essential in ad) — concurrency-safe drivers, real-time loops | confirmed (ad) |
| Embedded software | Listed as desirable; aligns with edge controller deployment | likely |
| Open-source surface | None publicly visible — software is commercial within the Niagara channel | confirmed (negative finding) |

Sources: ad essentials list + Tridium decks linked above.

## Synthesis — Cover-letter / interview angles

| # | Angle | Layer source | Best use |
|---|---|---|---|
| 1 | **PlantPRO is a digital twin → I built a digital twin (Battery Manufacturing Capstone)**. Same shape of problem, different domain. | Project | Cover letter P1 hook |
| 2 | **Real-time hardware control bottleneck is concurrent access, not algorithms** → CSIRO Modbus single-poller + interface-level cache + lock hierarchy → 3-month continuous run | Project + Stack | Cover letter P2 technical |
| 3 | **Multi-disciplinary collaboration ratio (devs + data scientists + engineers)** mirrors my CSIRO collaboration shape (researchers + electronics engineers + vendors) | Team | Cover letter P3 values |
| 4 | **Niagara is the honest gap; the surrounding shapes (digital-twin, edge, vendor-agnostic abstraction) are not** → 90-day plan: ship one PlantPRO module end-to-end on a Niagara controller before forming optimisation opinions | Project + Team | Cover letter P4 forward |
| 5 | **Energy-efficiency mission credibility** — the "Conserve It" name + chiller decarbonisation context — reasonable to acknowledge once without going mission-driven on tone | Company | One subtle reference, P1 or P4 |

## Open questions (interview prep)

- What does the team's release cadence look like for Niagara application updates? (Long deployment lifetimes vs. iteration speed tradeoff.)
- How is the ML training/retraining pipeline structured given the no-cloud-required constraint? On-controller? Customer-batch?
- What proportion of PlantPRO's logic is in Java/C++ vs. TypeScript/React (i.e. control-loop core vs. dashboards)?
- Is there a path from Graduate Software Developer to working closer to the ML/optimisation core, or is that owned by data scientists?
- Working model — is the team Melbourne-hybrid, full on-site, or distributed?

## Reading list (for the user, shortest → deepest)

1. [PlantPRO CORE — product page](https://www.conserveitiot.com/plantpro) — 5 min, the canonical product framing.
2. [Niagara Software — Conserve It](https://www.conserveitiot.com/niagarasoftware) — 3 min, confirms partner-tier role.
3. [Three new applications for Niagara 4 (Conserve It blog)](https://www.conserveitiot.com/post/conserve-it-releases-three-new-applications-for-niagara-4) — 5 min, recent team output.
4. [Tridium PDF — Conserve It Edge IoT Controllers (Chirayu Shah)](https://pages1.tridium.com/rs/808-SGM-271/images/ChirayuShah%20-%20Niagara%20at%20the%20Edge%20-%20Final.pdf) — 15 min, the deepest public technical view.
5. [YouTube — Introduction to Conserve It and PlantPRO](https://www.youtube.com/watch?v=Ct2jDipp530) — 5–10 min, founder/GM voice and tone.
