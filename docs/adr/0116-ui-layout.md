# 0116 — UI layout: mobile first, dark theme, a resource bar at the bottom

**Status:** Accepted · 2026-10-29

## Context

The frontend shows all the planet data on one page, almost without a layout.
That was enough for the first tests. Most players will use a phone, so the
UI must work on a small screen first. The layout starts to differ from
OGame here.

## Decision

- **Mobile first.** The base styles are for a screen width of 360 px. The
  Tailwind breakpoints `sm` and up only add to the layout. No horizontal
  scroll at 360 px. Each control that the player can tap is at least
  44 × 44 px.
- **Routes:**

  | Route | Page |
  |---|---|
  | `/homeworld` | The planets of the player. A tap on a planet opens its buildings. |
  | `/planets/[id]/buildings` | The buildings of one planet. |
  | `/planets/[id]/shipyard` | The shipyard of one planet. |

  `/planets` and `/` go to `/homeworld` for a logged-in player. Without a
  session, the pages go to `/login`, as today.
- **The app frame** for each page of a logged-in player:
  1. **A top bar:** the name of the selected planet, with a link to
     `/homeworld`, and the logout.
  2. **Section tabs** under the top bar, on the planet pages: Buildings and
     Shipyard. The tab of the open page is marked (`aria-current="page"`).
  3. **The content**, in one column on a phone. From `md`, the content can
     use two columns. The content has a bottom padding, so that the
     resource bar does not cover it.
  4. **A fixed resource bar at the bottom** of the screen, on the planet
     pages. It shows metal, crystal, deuterium, and energy
     (produced / used) of the selected planet. Each amount shows its
     capacity, and it is marked when it is at the capacity. The bar uses
     `env(safe-area-inset-bottom)`.
- **Dark space theme.** A near-black background, light text, and one
  accent color for the actions. Each resource has its own color, the same
  on each page. The colors are CSS variables in `globals.css`, used by
  Tailwind. The text contrast is at least 4.5 : 1 (WCAG AA).
- **Components.** Tailwind only, no new packages. Small shared components
  go in `src/components/ui/`, for example `Card`, `Button`, `Tabs`, and
  `ResourceAmount`. The feature components use them.
- **The page title** is "OOGame", not the Next.js default.

## Consequences

- No contract change, so this cycle has no `x-planned` flags and no
  cleanup PR.
- The agent can do all the work: `src/app/`, `src/components/`,
  `src/hooks/`, and `globals.css` are not guarded.
- The data hooks stay as they are. The vault data moves from the page to
  the app frame, so that the resource bar and the pages share it.
