---
name: opamp-knowledge
description: Shared design knowledge for the TwoStage Miller op-amp (45 nm). Load before reasoning about sizing, specs, or parameter changes.
---

# TwoStage op-amp: shared knowledge (all agents)

## Topology (from TwoStage.cir)
| Device | Role | Parameters |
|---|---|---|
| mn1, mn2 | NMOS differential input pair | mn1, wn1, ln1 (shared) |
| mp1, mp2 | PMOS current-mirror load (mp1 diode) | mp1, wp1, lp1 (shared) |
| mn3 | NMOS diode, bias reference, Ibias = 30 uA fixed | mn3, wn3, ln3 |
| mn4 | NMOS tail current source (mirrors mn3) | mn4, wn4, ln4 |
| mp3 | PMOS common-source 2nd stage (driver) | mp3, wp3, lp3 |
| mn5 | NMOS 2nd-stage current sink (mirrors mn3) | mn5, wn5, ln5 |
| Cc + Rc | Miller compensation + nulling resistor | cap, res |
Fixed: CL = 10 pF, VDD = 1.2 V, VCM = 0.6 V.

## Parameter grids (np.arange(min, max, step): upper bound EXCLUDED)
- m*: integers 1..24
- w*: 0.25u..2.75u, step 0.25u (meters, e.g. 1.0e-6)
- l*: 45n, 90n, 135n, 180n (meters)
- cap: 0.1p..9.9p, step 0.1p (farads)
- res: 0..9800, step 100 (ohms)
Call `simulate` with {"parameters": {...}} holding ALL 20 parameters. Off-grid values are rejected.

## Targets
Hard constraints: gain >= 200 V/V, ugbw >= 100 MHz, phm >= 60 deg,
slewRate >= 30 V/us, noise <= 30 mV RMS.
Optimization (minimize): area (target 2e-9 m^2), current (target 200 uA).

## Hand equations (first-order, use for reasoning)
Let S = m*W/L.
- Tail current: Itail = 30uA * S_n4 / S_n3
- 2nd-stage current: I_mn5 = 30uA * S_n5 / S_n3
- Total supply current ~ 30uA + Itail + I_mn5. Current is minimized, not limited, so a design may exceed 200 uA.
- Gain = gm_mn1/(gds_mn2+gds_mp2) * gm_mp3/(gds_mp3+gds_mn5)  -> longer L raises gain.
  Gain only needs to pass 200 V/V. Excess gain earns nothing and raises output noise, so do not lengthen L for more gain than you need. Use the shortest L that keeps gain above 200 with some margin. If gain is far above 200 and noise is failing, shorten L before adding current. The shortest grid L has very low output resistance, so it can collapse gain.
- UGBW ~ gm_mn1 / (2*pi*Cc), only if p2 is well above it. With CL = 10 pF, p2 is often lower, so this can overestimate UGBW several times. Then UGBW also depends on gm_mp3 (hypothesis: check by simulation).
- Do not use the square law for gm: this PDK's short devices do not follow it. Use gm = (gm/Id)*Id, with gm/Id at most about 20 /V for the input pair (weak inversion) and about 8-16 /V for mirrors and mp3 (device behaviour of this PDK).
- Non-dominant pole p2 = gm_mp3 / (2*pi*CL). With CL = 10 pF, 1 mS gives only 16 MHz. Always write p2 in MHz and compare it with UGBW. Do not aim for p2 above 100 MHz: that needs about 6-12 mS.
- All of these values are estimates. gm_mp3 and the exact p2 cannot be measured without operating-point data, so label any conclusion about them as hypothesis, and correct the estimate from the measured PM after each simulation.
- Phase margin: Rc above 1/gm_mp3 moves the zero into the left half plane, at about
  z = 1/(2*pi*Cc*(Rc - 1/gm_mp3)). Placed near UGBW it adds phase lead, so PM does not rely on p2 alone. Tune `res` for PM. 1/gm_mp3 is the lower limit for Rc.
  If Rc < 1/gm_mp3, then z is in the right half plane and harms PM (lowers PM). Don't do this.
  If Rc = 1/gm_mp3, then z is at infinity and does not help or harm PM.
  If Rc > 1/gm_mp3, then z is in the left half plane and adds phase lead at UGBW of about atan(UGBW / z).
  Making the zero harmless (Rc just above 1/gm_mp3) is not enough here. With CL = 10 pF, p2 = gm_mp3 / (2piCL) is often near or below UGBW, so PM needs real lead from the zero. Use this procedure:
  Estimate gm_mp3 = (gm/Id) * I_mn5, with gm/Id about 8-16 /V. Write 1/gm_mp3 in ohm.
  Write p2 in MHz and compare it with UGBW. Do not aim for p2 above UGBW by raising gm_mp3: that costs a lot of current.
  Choose a target zero z_t of about 0.5-1 x UGBW, and adjust it from measured PM. A lower z_t gives more lead but adds a pole-zero doublet that can slow settling.
  Set Rc = 1/gm_mp3 + 1 / (2*pi * Cc * z_t). Example: Cc = 0.5 pF and z_t = 50 MHz give Rc = 1/gm_mp3 + 6.4 kohm.
  Write z, its lead at UGBW, and the Rc used in the entry, before simulating.
  `res` is limited to 9800 ohm; if the formula exceeds this, raise Cc or z_t. Raising `res` also raises UGBW, so PM can stop improving or fall. Re-check z/UGBW after each simulation.
- Slew rate (rising edge only) ~ Itail / Cc, a rough estimate and not a bound: 30 V/us needs about Itail[uA] = 30 * Cc[pF]. Verify by simulation. mn5 does not set a lower limit on it. This estimate is often too high, especially at small Cc, so scale from your last measurement.
- Output noise ~ gain x input-referred noise, so it follows gain. More gm_mn1 lowers the input-referred part; less excess gain lowers the output noise directly.
- Systematic offset ~ 0 when (S_p3 / S_p1) = 2 * (S_n5 / S_n4). This holds only when lp1 = lp3 and ln4 = ln5, so keep those equal. It sets the output DC level (net6): a sudden large jump in gain or noise from a small change suggests net6 moved near a rail, with mp3 or mn5 leaving saturation (hypothesis).
- Prefer ln3 = ln4 = ln5 so the current mirrors copy accurately. This is a preference, not a requirement.

## What raises the FoM
With z(y) = (y - target) / (y + target), reward is the FoM:
- Not feasible: FoM = sum of violations (negative) + 0.05 * (-z(area) - z(current)). Fix hard constraints first.
- Feasible: FoM = 0.3 - z(area) - z(current). Only area and current count.
Margin beyond a hard constraint earns nothing. Once feasible, spend spare UGBW, slew rate, gain and noise margin on lower current and area, and calculate which of the two improves the FoM most for your next change. 
Required margins for a finished design: PM >= 62 deg, UGBW >= 105 MHz, slew rate >= 31.5 V/us, gain >= 210 V/V, noise <= 28.5 mV. A feasible design inside these margins is `thin`: it passes the hard constraints, but must be labelled as thin.

## Area facts (area_estimation.py), use them!
- Cc: 1 pF = 333 um^2 (3.3e-10 m^2). 6 pF alone uses the whole 2e-9 budget.
- Rc: 1 kOhm = 71 um^2; 9.8 kOhm = 700 um^2.
- Transistor finger W=1u, L=90n is about 0.42 um^2, so transistors are cheap.
=> Area is dominated by Cc and Rc. Keep Cc small (<= ~1.5 pF), and use only as much Rc as PM needs.
   Small Cc means UGBW rises, so keep gm_mn1 moderate to protect phase margin.

## Rules for every agent
1. Give a one-line physical reason for every parameter change.
2. Change few parameters per iteration (<= 4) so cause and effect stay traceable.
3. Never invent spec values. Only use numbers returned by tools.
4. Save details with the memory-log skill, and reply in the format your agent file gives.
