# AI image prompts

Prompts used to generate the project artwork. Re-run in DALL·E, Midjourney, Flux, or similar to create variations.

## Files

| File | Use |
|------|-----|
| `mina.png` | **Primary artwork** — README hero and Streamlit app |
| `mina-typewriter.png` | Alternate square illustration |
| `mina-typewriter-logo.png` | Icon variant (1:1) |
| `mina-typewriter-banner.png` | Banner variant (16:9) |

## Primary prompt

```text
Centered portrait composition of Mina Harker inspired by Bram Stoker's Dracula — a composed Victorian woman in her late twenties, dark hair neatly pinned, high-collared blouse and modest period dress, calm focused expression. She sits at an antique manual typewriter, fingers mid-typing. From the air around her, golden-orange ethereal aura patterns spiral inward: luminous filaments, soft sound-wave ripples, and faint floating letters dissolving into text on the page, as if she is gathering whispers and speech from the atmosphere and transcribing them. Warm amber and gold light glows behind her like a halo of information. Dark muted background with subtle Victorian study details — bookshelves, lamp, paper stacks — softly out of focus. Cinematic lighting, painterly digital illustration, rich detail, symmetrical centered framing, no horror violence, no fangs, no blood, elegant and intelligent atmosphere.
```

## Logo add-on

Append to the primary prompt:

```text
... simplified composition, icon design, clean edges, Mina and typewriter readable at small size, dark navy background, glowing gold aura as the main accent color, tight crop on upper body and typewriter, simple readable silhouette.
```

## Banner add-on

Append to the primary prompt:

```text
... wide 16:9 banner, Mina slightly smaller, more empty space on sides for title overlay.
```

## Negative prompt (Stable Diffusion / ComfyUI)

```text
vampire fangs, blood, gore, horror monster, Dracula cape, cheesy Halloween, modern laptop, smartphone, neon cyberpunk, cartoon chibi, low quality, blurry, extra fingers, deformed hands, watermark, text logo, oversaturated, ugly, cluttered
```

## Palette

- Gold: `#D4A853`
- Amber: `#E8943A`
- Background: `#1a1a2e`
