# Bridge-App (Tauri)

Lokale Orchestrierung: Dateizugriff, Queue, Upload/Download, HTTP-Client zur API.

## Gerüst

Für ein vollständiges Tauri-Projekt (nach ADR 002):

```bash
cd apps/bridge
pnpm create tauri-app@latest .
```

Bis dahin existiert ein minimales Rust-Binary als Platzhalter (`src/main.rs`), damit `cargo build` im Ordner funktioniert.
