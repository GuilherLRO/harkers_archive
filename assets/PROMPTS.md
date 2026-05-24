# Harker's Archive — AI image prompts

Root monorepo artwork. Parent mark to [Dr. Seward's Phonograph](../sewards_phonograph/seward-phonograph/PROMPTS.md) (purple — recording) and [Mina's Typewriter](../mina_typewriter/assets/PROMPTS.md) (gold — transcribing).

**Concept:** *The compiled record* — a **stack of aged papers** with an envelope on top, like Mina's finished documentation of every source. A **single sea-glass teal aura** swirls around the stack; floating letters and symbols inside the mist represent information arriving from many directions. The project name appears in **glowing gold serif letters** on the top page.

**Visual reference:** [`inspiration-reference.png`](inspiration-reference.png) — mood and composition guide.

**Canonical logo:** [`harkers-archive-logo.png`](harkers-archive-logo.png) — approved; includes leather stitched frame.

## Files

| File | Use |
|------|-----|
| `inspiration-reference.png` | User reference — mood and composition guide |
| `harkers-archive-logo.png` | **Canonical logo** — README hero, repo identity (with frame) |
| `harkers-archive-logo-noframe.png` | Logo variation — same subject, plain dark background, no canvas/frame |
| `harkers-archive-primary.png` | Primary square — full detail hero |
| `harkers-archive-logo-v2.png` | Alternate logo crop |
| `harkers-archive-banner.png` | Wide banner (16:9) |

## Primary prompt (reference-inspired)

```text
Centered square composition for Harker's Archive, inspired by archival correspondence artwork. A stack of aged cream parchment papers with frayed edges, cursive handwriting and faint postmarks visible on the sheets — many sources compiled into one record. A cream envelope rests on top of the stack with teal wax seal. On the top page, glowing gold serif letters read exactly: HARKER'S ARCHIVE — luminous amber-gold (#D4A853), elegant and legible, NOT cursive handwriting. A sea-glass teal and jade ethereal aura swirls in a circular vortex around the stack: luminous mist, soft ripples, and floating white-teal letters, numbers, and symbols suspended in the glow like information gathering from many directions — teal only (#4ECDC4, #2A9D8F), no purple, no orange in the aura. Dark textured navy-black background like aged leather, subtle square stitched frame border with rounded corners. Painterly digital illustration, scholarly mystical mood, no human figures, no horror, no modern objects.
```

## No-frame variation prompt

Same subject as the canonical logo — remove only the canvas:

```text
Identical central subject to harkers-archive-logo.png: aged parchment stack, cream envelope with teal wax seal H, gold serif HARKER'S ARCHIVE on top page, sea-glass teal aura with floating letters and symbols. Plain solid dark navy-black void background #1a1a2e — NO leather mat, NO stitched frame, NO border, NO canvas. Subject floating centered in empty dark space. Same painterly style and colors.
```

## Logo add-on

Append to the primary prompt:

```text
... slightly simplified for logo use, cleaner silhouette, tighter crop on stack and teal aura, reduce fine texture noise, keep stacked papers envelope gold serif title and stitched frame readable at small size, emblem-friendly.
```

## Banner add-on

Append to the primary prompt:

```text
... wide 16:9 banner, paper stack slightly smaller, generous empty space on left and right for title overlay, single teal aura spiraling inward, gold serif HARKER'S ARCHIVE on top page preserved, leather frame preserved.
```

## Negative prompt (Stable Diffusion / ComfyUI)

For **no-frame** variant, also append:

```text
leather frame, stitched border, mat border, picture frame, square border, rounded corner frame, canvas
```

Full negative list:

```text
cursive title, calligraphy title, handwritten project name, single lonely paper sheet, purple aura, orange aura, amber aura streams, multicolor rainbow, filing cabinet, archive boxes, vault door, vampire fangs, blood, gore, horror, modern smartphone, laptop, neon cyberpunk, cartoon chibi, low quality, blurry, watermark, wrong text, misspelled title, illegible letters, oversaturated, ugly, horn pressed to ear
```

## Palette

| Role | Hex | Notes |
|------|-----|-------|
| Title gold | `#D4A853` | Glowing serif project name on top page |
| Paper | `#F0E6D0` | Cream stack |
| Aura (only) | `#4ECDC4` | Sea-glass teal — core |
| Aura deep | `#2A9D8F` | Jade shadow in filaments |
| Background | `#1a1a2e` | Dark navy — leather+frame (logo) or plain void (noframe) |

**Do not use** purple or amber in the aura — those belong to sub-project heroes only.

## Concept pairing with sub-projects

| | Harker's Archive | Dr. Seward's Phonograph | Mina's Typewriter |
|--|------------------|-------------------------|-------------------|
| Role | Parent — **compiled stack** | Capture voice | Transcribe voice |
| Focus | **Many pages + gold serif title** | Phonograph | Typewriter |
| Aura | **Teal only**, multi-direction | Purple inward | Gold inward |
| On-page text | **HARKER'S ARCHIVE** (gold serif) | — | — |

## Re-run checklist

1. **Canonical:** `harkers-archive-logo.png` — keep as approved default.
2. **No-frame:** `harkers-archive-logo-noframe.png` — same subject, no canvas.
3. Verify spelling: **HARKER'S ARCHIVE** (exact), in **serif type** not cursive.
4. Keep aura **teal only** — reject multicolor outputs.
5. Update root [README.md](../README.md) hero — uses canonical logo.
