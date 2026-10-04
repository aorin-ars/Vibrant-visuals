// VYSE Weather Sync
//
// The game's own bug: reopen a world while it rains and the sky comes back
// clear - full sun, no rain darkening - with rain falling, until the weather
// next changes. A resource pack cannot touch weather, but resending it
// fixes the sky: a moment after a player joins, if it is raining, stop the
// rain for two ticks and start it again (thunder stays thunder). The rest of
// the rain's duration is picked anew by the game.

import { world, system, WeatherType } from "@minecraft/server";

const KEY = "vyse:weather";
const DELAY = 60;            // ticks after joining (3 s), once the world has settled

function name(ev) {
  // Newer API: newWeather. Older: raining / lightning flags.
  if (ev.newWeather !== undefined) return ev.newWeather;
  if (ev.lightning) return WeatherType.Thunder;
  return ev.raining ? WeatherType.Rain : WeatherType.Clear;
}

// Remember the weather, for game versions without Dimension.getWeather().
world.afterEvents.weatherChange.subscribe((ev) => {
  try {
    world.setDynamicProperty(KEY, name(ev));
  } catch {
    // Read-only moments: the next change will be recorded.
  }
});

function currentWeather(overworld) {
  if (typeof overworld.getWeather === "function") return overworld.getWeather();
  return world.getDynamicProperty(KEY);
}

world.afterEvents.playerSpawn.subscribe((ev) => {
  if (!ev.initialSpawn) return;
  system.runTimeout(() => {
    const overworld = world.getDimension("overworld");
    const weather = currentWeather(overworld);
    if (weather !== WeatherType.Rain && weather !== WeatherType.Thunder) return;
    overworld.setWeather(WeatherType.Clear, 2);
    system.runTimeout(() => overworld.setWeather(weather), 2);
  }, DELAY);
});
