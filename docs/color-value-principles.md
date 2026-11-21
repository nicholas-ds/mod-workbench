# Color and value principles (research for the calm theme)

Date: 2026-11-12. Asked by the author: is there a rule for how much of a page may be bright or saturated, and what makes color easy to read? The eye-comfort rules (`docs/eye-comfort.md`) already cover dark mode, saturation and contrast. This file adds what the new search found and how the calm theme uses it.

## What the search found

- **60-30-10.** A proportion guide: about 60% dominant color, 30% secondary, 10% accent. It is approximate and a starting point, not a law. An accent must stand out from the dominant color to do its job. ([UX Planet](https://uxplanet.org/the-60-30-10-rule-a-simple-way-to-creating-catchy-user-interfaces-e9e2cf957213), [LogRocket](https://blog.logrocket.com/ux-design/60-30-10-rule/))
- **Contrast for text.** WCAG 2.2 asks for 4.5:1 for normal text and 3:1 for large text. APCA is a newer model. Its sources disagree on the body-text floor (Lc 60 or Lc 75). Light text on dark needs more care than the ratio alone shows. Treat APCA as a second check, not the rule. ([W3C APCA notes](https://www.w3.org/WAI/GL/task-forces/silver/wiki/Visual_Contrast_of_Text_Subgroup/APCA_model), [Myndex](https://www.github.com/Myndex/SAPC-APCA/discussions/30))
- **Not found.** The search found no source that gives a number for "only X percent of a page may be saturated" or for the squint test. Do not quote such a number as fact.

## How the calm theme applies it

- Large areas (rail, whiteboard, questions panel) lose about 32% of their saturation and keep their lightness. Brighter surfaces would glare more on the dark page.
- Small accents (tags, buttons, chips) lose 10% to 18%. They stay the strongest colors on screen. This follows the accent role in 60-30-10.
- The highlight on every clay shape drops from 42% to 28% white.
- Dim text on the dark page goes from 7.6:1 to 9.3:1.
- Dark ink on every clay and accent color stays at 4.9:1 or higher (the rule is 4.5:1). `tests/test_theme_contrast.py` checks this for both themes.
- Hues do not change, so the StarExplorer palette rule holds.
- The message dock keeps the classic colors in both themes (author request).

Unverified: whether the calm values feel right for long sessions. That is the author's call (board calm-theme-review).
