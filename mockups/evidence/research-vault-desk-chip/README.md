# Research Vault desk-type chip — visual evidence

Neutral metadata chip (never semantic state color). Same quiet-chip idiom in both themes.

Intentionally differing mechanisms: NONE.
DARK: hairline `var(--line)`, muted foreground `var(--muted)`, transparent fill, no glow.
LIGHT: same tokens (light research-workspace remaps `--muted`/`--line`), no shadow.

Matrix (card crop, stamp visible): dark/light × EN/ZH × 1440/390 = 8.

| file | theme | lang | viewport |
|---|---|---|---|
| `dark-en-1440.png` | dark | en | 1440 |
| `light-en-1440.png` | light | en | 1440 |
| `dark-zh-1440.png` | dark | zh | 1440 |
| `light-zh-1440.png` | light | zh | 1440 |
| `dark-en-390.png` | dark | en | 390 |
| `light-en-390.png` | light | en | 390 |
| `dark-zh-390.png` | dark | zh | 390 |
| `light-zh-390.png` | light | zh | 390 |

r3 extra crops (baked SSR, JS stripped so hydrate cannot stomp). Two frames: the lane chip and the folder-institution card are not in the same region, so they are not combined.

| file | what it shows |
|---|---|
| `badge-saved-none-yet-zh-1440.png` | Saved lane chip baked as 「暂无」 (worded null, not `0` or `—`). dark / zh / 1440. |
| `folder-inst-desk-zh-1440.png` | Folder-named institution `S&T` renders 机构研究台, not the folder string. The pin is ★ 精选 (bilingual Highlighted pair). dark / zh / 1440. |
