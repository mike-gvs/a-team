# gvs-ui

Shared UI kit for Gold Valley Solutions packages. Plain CSS and a small vanilla JS theme toggle. No framework.

Pin a version in the URL:

```html
<!-- gvs-ui@0.1.0 -->
<link rel="stylesheet" href="/gvs-ui/0.1.0/css/tokens.css">
<link rel="stylesheet" href="/gvs-ui/0.1.0/css/components.css">
```

Product apps may set `--gvs-accent` in one `theme.css`. Do not override color or spacing tokens elsewhere.

Includes: layout shell, header/footer, buttons, forms, tables, chat panel, status badges, wizard steps. Dark and light themes. Keyboard focus styles and a 390 px layout.
