# Changelog

## 0.3.1 beta

- Assign a stable Windows application identity before creating any windows so
  the taskbar uses Quiet Quota's static mint Q instead of the Python identity.
- Keep the quota-dependent ring and colours exclusive to the tray icon.

## 0.3.0 beta

- Add a guided connection window, offered automatically when Codex or sign-in is missing.
- Add Connection actions to the tray and Settings without adding a Settings row.
- Launch Codex-managed ChatGPT browser sign-in only on an explicit click.
- Confirm connection only after reading weekly quota; distinguish login from quota availability.
- Support retries, browser reopening, cancellation and a five-minute login timeout.
- Reuse existing credentials; restart the quota reader after connecting to avoid stale account data.
- Translate the flow into all eight languages and add authentication/UI regression tests.

## 0.2.7 beta

- Place the compact Ko-fi button at the right of the Animation row.
- Show the coffee icon after the text and remove the extra support row.
- Match the support button to the native Save/Cancel button size in each language.

## 0.2.6 beta

- Restyle the Settings Ko-fi button with a coffee-cup icon and subtle rounded border.
- Place support on its own row above Cancel, aligned to the right.

## 0.2.5 beta

- Change tray and popup colours to yellow at 50% remaining and red at 20% remaining.
- Keep configurable popup alert thresholds unchanged.

## 0.2.4 beta

- Make the tray Q ring proportional to remaining weekly quota, with a full ring at
  0% used and an empty ring at 100% used; keep the Q tail visible in the status colour.
- Keep green/amber/red based on usage, updating the ring on each successful reading.
- Show a neutral grey icon while waiting for data or when usage is unavailable.
- Keep title-bar and shortcut branding unchanged; test popups preserve the live icon.

## 0.2.3 beta

- Add a discreet Ko-fi link to the Settings footer, with a translated tooltip.
- Open the support page only on an explicit click, without saving or closing Settings.
- Add a crisp quota-ring Q icon for the title bar and tray, plus a Windows shortcut ICO.

## 0.2.2 beta

- Apply screen corner, monitor and animation changes immediately, alongside language.
- Save persists changes; Cancel, closing Settings or failed saves restores previous visual settings.
- Thresholds, display duration and polling interval still apply only after Save.
- Cover monitor relocation, timer preservation and animation changes in regression tests.

## 0.2.1 beta

- Preview language changes immediately throughout the app, including visible popups.
- Save persists the selection; Cancel, closing Settings or a failed save restores the previous language.
- Keep the popup's timeout and animation progress when changing language; do not trigger extra notifications.
- Add regression checks for live switching, saving, cancellation and failed saves.

## 0.2.0 beta

- English is the default UI language, including fallback for older settings.
- Add German, Spanish, French, Portuguese, Italian, Japanese and Simplified Chinese.
- Change language in Settings; apply immediately and remember it across launches.
- Translate popups, tray actions, settings and app-generated error messages.
- Size the popup to translated text; keep text and percentage in separate columns.
- Use English filenames throughout, including Setup.cmd, Start.cmd and Diagnostics.cmd; remove German launcher aliases.
- Add public-facing documentation, privacy information and localisation tests.

## 0.1.0 private test

- Initial German Windows tray app with fixed threshold alerts, persistence,
  non-interactive popup, demo mode and Codex app-server usage reader.
