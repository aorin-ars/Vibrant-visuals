# Vibrant Visuals check pack

A yes/no answer, not a look.

The lighting values in `lighting/global.json` are read by Bedrock's deferred
renderer and by nothing else. So:

| What you see | What it means |
|---|---|
| The world turns **bright magenta** | Deferred rendering is running **and** this pack reached it. Any pack of this kind will work — the main pack just needs tuning. |
| The world looks **completely normal** | One of those two is false. Either Vibrant Visuals is off (or unsupported on this device), or the pack is not actually active on the world. Until that is fixed, no pack of this kind can change anything. |

Ambient is pushed far past any sane value so the answer cannot be mistaken for a
subtle tweak, and the sun is dropped to near nothing so the magenta is not
washed out by daylight.

Remove the pack once you have your answer.
