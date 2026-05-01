# ADR 002 — Bridge-Implementierung auf Tauri (Rust Kern)

- **Status:** Akzeptiert
- **Datum:** 2026-05-01
- **Entscheider:** Maintainer

## Kontext

Die Bridge übernimmt Dateisystem-, Netzwerk- und lokale Zuverlässigkeitsaufgaben zwischen Lightroom-Plugin und Backend. Sowohl **Electron** als auch **Tauri** waren Optionen aus dem Ursprungsdokument.

## Entscheidung

Primär **Tauri** mit Rust-Kern verwenden für:

- kleinere Artefakte und geringere Laufzeit-Grundlast,
- strukturierten Zugriff auf native Dialoge/OS-Integration,
- Sichereres Sandboxing-Konzept im Vergleich zu einem immer bundelnden Chromium-Shell-Prozess.

Ein **Electron**-Pivot bleibt bewusst möglich, falls das Team stark in TypeScript-heavy Integrationsarbeit steckt; alle Netzwerkverträge sitzen bereits in [`packages/contracts`](../../packages/contracts), sodass nur die lokale Implementierung austauscht.

## Folgen / Trade-offs

- **Positiv:** Passend zu schlankem Plugin + Cloud-Heavy ML-Stack ohne zweiten „schweren“ Runtime-Footprint.
- **Negativ:** Web-Teams brauchen Rust/TS-Brücke beim UI; höhere Einarbeitung gegenüber klassischem Electron.
