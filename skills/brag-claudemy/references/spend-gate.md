# Spend gate

Nothing that costs money runs until BRIEF.md has an approved line under "Spend approved".

## What costs money (as recorded 2026-10-23)

- Still images: gpt-image-2 through scripts/gen_image.py, 1536x1024, quality high. Key read from the file named by BRAG_OPENAI_KEY_FILE (default ~/.config/brag/openai-key). Never print or copy the key.
- Motion clips: Kling 2.6 through the Apify actor pnda/kling-video-generator, about $0.63 to $0.70 per pro-second; six 5-second clips cost about $19 to $21. A test clip cost about $3.50 to $3.80 (Kling and Hailuo H3 each).
- Retired or broken: Sora 2 API (shut down 2026-09-24), Gemini image (402, credits depleted on 2026-10-23).

Prices change. Re-check the actor's pricing before quoting a number.

## The gate

1. Write the plan: what will be generated, how many, which tool, the estimated cost (count x unit price).
2. Test round first: one shot in two tools, side by side, the founder picks. Cost of the test is part of the estimate.
3. Ask for approval with the total. Do not start on silence.
4. Write the approved line in BRIEF.md ("Spend approved: up to $X for ...") and the same line in plan.md.
5. After each generation, append the actual cost to plan.md. Stop at the approved total and ask before going over.

If the first cut can be built without generation (route R1), do that first. Prove the shape by hand, then decide whether to spend.
