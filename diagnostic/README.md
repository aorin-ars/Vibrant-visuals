# Vibrant Visuals check pack

This pack answers one question in one go: **why is nothing happening?**

It changes two independent things:

1. **Lighting** (`lighting/*.json`) — read by the deferred renderer and by
   nothing else. Ambient is pushed far past any sane value and tinted magenta.
   Every lighting identifier the vanilla biomes use is overridden, not just
   the global one: since 1.21.90 most biomes (jungle, desert, taiga, mesa,
   the Nether, the End, ...) have their own lighting that wins over
   `lighting/global.json`, so a global-only test reads "off" in those biomes
   even when the renderer is running.
2. **Block textures** (`textures/blocks/*.png`) — plain texture replacement,
   which works on any renderer. Dirt, stone, cobblestone, sand, gravel, oak
   planks, oak log and grass become lime green with a black X.

Look at any dirt or stone near you, in daylight:

| What you see | What it means | What to do |
|---|---|---|
| Everything bathed in **magenta light** (and the blocks are lime X) | Deferred rendering is running **and** the pack reached it | Nothing is broken — the main pack just needs its numbers tuning |
| Blocks are **lime green with a black X**, but the light is normal | The pack **is** active, but Vibrant Visuals is **off or unsupported** | Turn on Settings → Video → Vibrant Visuals. If the toggle is missing or greyed out, the device or version does not support it, and no pack of this kind can do anything |
| **Nothing changed at all** | The pack is **not active on this world** | Re-import it and activate it in the world's Settings → Resource Packs, then rejoin the world |

Remove the pack once you have your answer.
