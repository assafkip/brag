# Route R3: Hyperframes beats (the 2026-10-15 Claudemy app tour)

Use this when the founder asks for Hyperframes, or when a long product tour with many UI beats is the goal. It uses the installed website-to-video skill and the Hyperframes skills; do not copy them here.

## Steps

1. Capture the live product (website-to-video step 0) when STATUS is BUILT. For a concept there is nothing to capture: write DESIGN.md as a proposal and get the founder's pick.
2. DESIGN.md, then BRIEF.md, then STORYBOARD.md approved before any build.
3. Write a BUILD-BRIEF for beat sub-agents with: project root, the read-first list (the website-to-video beat-builder guide, STORYBOARD.md, DESIGN.md, the reference screenshots, BRIEF.md), a timing contract (beat id, start, duration; 0.5 s crossfade overlaps; the beat's internal GSAP timeline spans exactly its duration), brand values, fonts, captured icons, rules (real copy only, no emdash or double hyphen, no Math.random, no repeat:-1, no bare gsap.to, nothing from confidential material), and a stop rule: if the same lint or snapshot failure happens twice after a fix, stop and report the diagnosis.
4. One sub-agent per beat. Each builds, lints, snapshots, views its frames and reports: path, lint error count, frames viewed, deviations.
5. Render with Hyperframes, then run the website-to-video verifier and this skill's verify.py. Report FAILs verbatim.

## Lessons from the first tour

The verifier failed three checks: no captured brand assets used (rebuilding them in CSS erased what makes the brand recognizable), headline text under the 80 px floor, and beats under 70 percent timeline coverage. Fix those at the storyboard, not after the build.
