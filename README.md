# lisan-site

Landing page for [Lisan](https://github.com/Moshe-ship/Lisan) — Arabic-first local dictation for macOS.

Single-file static HTML. No build step. Deploys via GitHub Pages from the root.

## Local preview

```bash
open index.html
```

## Design notes

- Dark void background (`#050507`) with scanline overlay
- Accent: soft cyan (`#7dd3fc`)
- Fonts: Noto Kufi Arabic + JetBrains Mono via Google Fonts
- RTL-primary (`<html dir="rtl">`), LTR islands for code blocks
- Breakpoints: 900 / 768 / 480 / 375 + landscape + `env(safe-area-inset-*)`

## License

MIT
