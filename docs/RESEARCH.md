# Research basis

Every claim in the AstraOps problem statement is sourced below. The purpose of this
document is to show that the gap the project addresses is documented in the peer-reviewed
literature and in agency reporting, not asserted.

---

## 1. The orbital environment is crowded, and the crowding is measured

ESA's Space Debris Office maintains the authoritative public statistics. As of its
31 July 2026 update, space surveillance networks regularly track roughly **46,160 objects**
in Earth orbit. Around **16,000** of those are functioning satellites. The rest are dead
spacecraft, spent rocket bodies, hardware released during missions, and fragments from more
than **660** recorded break-ups, explosions and collisions.

Tracking has a floor. Objects below roughly 10 cm in low orbit are generally too small for
ground-based radar and optical sensors. ESA's MASTER-8 model estimates a further
**1.2 million objects between 1 and 10 cm** and **over 140 million larger than 1 mm** that
are not catalogued. A 1 cm aluminium fragment at orbital velocity carries enough kinetic
energy to destroy a spacecraft.

The operationally relevant figure: ESA calculates that satellites in the **500–600 km band
encounter roughly 30 close approaches per year** on average. Collision avoidance in that
regime has shifted from an occasional response to specific warnings into a continuous
operational burden.

> Sources: ESA Space Debris Office, *Space Environment Statistics* (sdup.esoc.esa.int);
> ESA *Annual Space Environment Report*, 10th edition (1 May 2026); ESA MASTER-8 model,
> reference population 08/2024.

---

## 2. Space weather destroys spacecraft, and the warning scale does not warn about it

This is the core of the project's argument, and it is documented precisely.

**What happened.** On 3 February 2022 at 18:13 UTC, SpaceX launched 49 Starlink satellites
into a 210 × 350 km staging orbit, intending to raise them to an operational 550 km. The
launch took place during the recovery phase of a geomagnetic storm rated **G1 — the mildest
category on NOAA's five-step scale**. SpaceX reported atmospheric drag up to **50% higher**
than on previous launches. Despite commanding the satellites into a low-drag edge-on
configuration, **38 of the 49 could not be recovered** and re-entered on or about 7 February.
Estimated loss: tens of millions of dollars.

**Why it happened.** Berger et al. (2023) showed thermospheric density at 210 km was at
least **20–30% higher** than in the nine days preceding launch, driven by consecutive
geomagnetic storms following solar eruptions from active region 12936.

**Why the warning system did not help.** Fang et al. (2022), writing in *Space Weather*,
found that no alerts or warnings issued by NOAA's Space Weather Prediction Center were
directed at satellite operators concerned with atmospheric drag. They concluded that alerts
based on neutral density predictions are needed to prevent drag-driven satellite losses and
to support collision avoidance calculations.

**The underlying mismatch.** NOAA's G-scale was calibrated around ground effects — power
grid currents and HF radio disruption. It was never calibrated for what a small storm does
to air density at 210 km. A storm that barely registers for a transformer can remove forty
satellites from orbit.

**It was not a one-off.** Twelve Starlink satellites were lost during the extreme
geomagnetic storm of 10 May 2024 through the same mechanism.

> Sources: Berger, T. E. et al. (2023), "The Thermosphere Is a Drag: The 2022 Starlink
> Incident and the Threat of Geomagnetic Storms to Low Earth Orbit Space Operations",
> *Space Weather*, 10.1029/2022SW003330 — open access. Fang, T.-W. et al. (2022), "Space
> Weather Environment During the SpaceX Starlink Satellite Loss in February 2022",
> *Space Weather*, 10.1029/2022SW003193. Dang, T. et al. (2022), 10.1029/2022SW003152.
> Baruah, Y. et al. (2024), 10.1029/2023SW003716.

---

## 3. Small operators have spacecraft but not operations infrastructure

The Aerospace Corporation's review of CubeSat mission outcomes found **academic success
rates averaging around 45%**, where success is defined as operating on orbit for 60 days or
more. Independent analyses put **40–50% of university-class CubeSat missions** as failing to
achieve their primary objectives.

The failure causes matter here. Surveys of academic, commercial and government CubeSat
developers identified the **communication system, the ground segment, and power systems** as
the most common problem areas. Ground segment — the operational side, not the spacecraft —
appears repeatedly.

This is the accessibility gap. University teams and small operators can build and launch a
spacecraft. What they lack is the situational awareness infrastructure that a national
agency takes for granted.

> Sources: The Aerospace Corporation, *8 Steps to Improving Small Sat Mission Success*;
> Swartwout, M., Saint Louis University, CubeSat mission-status survey; Langer & Bouwmeester
> (2016), 30th AIAA/USU Conference on Small Satellites.

---

## 4. What follows from this

Three findings, taken together, define the problem AstraOps addresses:

1. The data is **public, free and continuous**. CelesTrak publishes orbital element sets;
   NASA DONKI publishes solar flares, CMEs and geomagnetic storms in near real time.
2. The translation from that data to an operational decision requires expertise in orbital
   mechanics, heliophysics, and the literature — and Fang et al. establish that for drag
   specifically, **nobody is publishing that translation at all**.
3. The operators least able to bridge that gap are the ones **growing fastest in number**.

AstraOps builds the missing layer. It ingests the same public feeds, computes the physics
deterministically — SGP4 propagation, pairwise conjunction screening, NOAA-scale impact
classification — and uses IBM Granite only for what language is actually for: explaining
what the computed result means and what an operator should do about it.

The architectural separation is deliberate. The language model never performs arithmetic.
Every figure the system reports is derived from orbital mechanics or read from a published
feed. The model's system prompts explicitly forbid stating values that are not present in
its input, which is why the generated briefs describe magnitude in words where the data does
not support a number.

---

## Limitations we state rather than hide

- **Screening scope.** Pairwise conjunction screening is O(n²). AstraOps screens the first
  150 objects of a group; full-catalogue screening requires a spatial index and is out of
  scope for this build. The interface reports how many objects of the group were screened.
- **Collision probability.** Pc assumes an isotropic 200 m position covariance and a 20 m
  combined hard-body radius. These are screening defaults, not operator-supplied covariances,
  and the figure should be read as a relative ranking rather than an absolute probability.
- **Display positions.** Geodetic coordinates for the globe use a spherical Earth, which is
  adequate for display and inadequate for navigation.
- **Data freshness.** CelesTrak refreshes each group every two hours and rate-limits clients
  that poll harder. The system falls back to the last known good element set rather than
  showing nothing, and surfaces the element-set age in the interface.
- **Drag model.** The drag-decay estimates in `services/drag.py` are deliberately simplified
  and their assumptions are stated in the code. The quiet-time base densities are
  representative values — 2.5 × 10⁻¹⁰ kg/m³ at 210 km, 2.8 × 10⁻¹² kg/m³ at 400 km, and
  5.0 × 10⁻¹³ kg/m³ at 550 km — drawn from standard NRLMSISE-00 outputs at solar minimum.
  They are not dynamically queried from a thermospheric model. The density multiplier
  `1.0 + 0.10 × Kp` is a linear approximation anchored to the February 2022 event where
  a Kp of roughly 5 coincided with densities 50 % above quiet-time at 210 km; the true
  relationship is non-linear and saturates at high Kp. The ballistic coefficient (`Cd = 2.2`,
  `A/m = 0.01 m²/kg`) is representative of a 3U CubeSat in a tumbling attitude; actual
  values depend on satellite geometry and attitude control. Because density grows steeply
  below 300 km, the linear multiplier understates decay in VLEO: the code flags altitudes
  below this band with a plain-language caveat ("orbit not sustainable, reentry in days")
  rather than a precise number. These figures are inputs to the Granite brief; the model
  is instructed to cite them, not to improve on them.
