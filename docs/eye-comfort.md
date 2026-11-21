# Eye comfort rules

Purpose: the author works in the workbench for long hours. These rules keep the colors nice and easy on the eyes. They apply to every palette in `docs/design-standard.md`.

## What the research says

- Do not use pure black or pure white. Use dark grey surfaces and off-white text. Sources report that white on black strains the eyes more than light mode. ([Smashing Magazine](https://shop.smashingmagazine.com/2025/04/inclusive-dark-mode-designing-accessible-dark-themes/), [UX Planet](https://uxplanet.org/designing-in-dark-mode-b696251c7483))
- Saturated colors vibrate on dark backgrounds and cause strain. Use desaturated colors instead. One rule of thumb is about 20 points less saturation than in a light theme. ([Material Design dark theme](https://m2.material.io/design/color/dark-theme), [Atmos](https://atmos.style/blog/dark-mode-ui-best-practices))
- Text needs at least 4.5:1 contrast (3:1 for large text). Very high contrast also strains the eyes. Aim for a balance. ([Fivejars](https://fivejars.com/insights/dark-mode-ui-9-design-considerations-you-cant-ignore/), [Glance](https://thisisglance.com/learning-centre/how-do-i-make-sure-my-apps-dark-mode-doesnt-strain-users-eyes))
- Material Design uses the 200 tone of a color on dark surfaces. That tone is lighter and softer than the brand color and still passes 4.5:1.
- Dark mode helps mainly in low light. In a bright room it can backfire.

Not verified: halation (light bleeding around bright text). The search found nothing on it. The 7:1 figure for Apple body text and the 15.8:1 figure I searched for were not confirmed.

## Rules for this project

1. Surface colors (large areas): saturation 45% or lower, lightness 54 to 60%.
2. Accent colors (small areas): saturation 50% or lower. Accents may be a little brighter than surfaces.
3. Text on the table is off-white cream (`#E0DAC2`, about 12:1), never pure white. The table is `#1E1724`, never pure black.
4. Dark ink text on any clay color must reach 4.5:1 or higher. Measure it before a color enters a palette.
5. Large bright areas tire the eyes most. Keep big panels calm and put the stronger colors on small controls.
6. Greyscale stays available as a rest mode.
7. Keep motion small (the stop-motion wobble is about 1 px) and off for reduced motion.

## Result

The author chose the StarExplorer palette. Pure comfort tuning looked washed out, so the author set 70% vibrancy: 70% of the way from the comfort set to the original colors. Dark ink contrast is 4.8:1 or higher on every clay color. The locked values are in `docs/design-standard.md` and `web/tokens.css`.
