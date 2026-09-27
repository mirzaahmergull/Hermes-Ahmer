# Hermes-Ahmer: Ahmer's personal Hermes fork

Read this file before changing, building, installing, or updating this fork.
This fork is for Ahmer's own use. It keeps official Hermes capabilities and
upstream contributions while maintaining Ahmer's fixes and custom development.
The user owns this policy; upstream AGENTS.md still governs coding conventions.

## Separation of development, builds, production, and user data

- Development source: `C:\dev\Hermes-Ahmer`. Editing it MUST NOT change production.
- Build workspaces and caches: `C:\dev\Hermes-Ahmer-builds`.
- Production: `C:\Hermes-Ahmer\releases\<commit-and-build-id>`.
- Stable launchers and active-release record: `C:\Hermes-Ahmer\bin` and
  `C:\Hermes-Ahmer\active.json`.
- Production home: `C:\Users\mirza\AppData\Local\hermes`. Keep it in place.
  Skills, configuration, credentials, auth, conversations, databases, memories,
  plugins, cron, pairing and all user state stay here. Never replace it with
  sample config, copy secrets into Git, or point developer tests at it.
- Development home: `C:\Users\mirza\AppData\Local\Hermes-Ahmer-dev`.
  Build and candidate tests use disposable homes outside production.
- Retain the original installation and previous production releases. No
  automatic uninstall, pruning, release deletion, or destructive clean command.

## Release workflow

Commit reviewed changes first. `ahmer-release build` snapshots an exact clean
fork commit into an independent build checkout, builds the native package and
frontends, and runs candidate checks against an isolated home. Production must
not import code, editable packages, frontend assets, or dependency files from
the development checkout. A build is not a deployment.

`ahmer-release deploy` promotes a verified candidate, gracefully stopping the
gateway, backing up production user data and launcher scripts, switching the
active release, regenerating gateway launch scripts and checking liveness.
The existing scheduled task continues to use the existing home. Changes to
database schemas require the matching data backup for an older-code rollback.
`ahmer-release status` reports installed/candidate revisions.
`ahmer-release rollback` selects the previous release; restore its recorded
state backup if a schema migration makes old code incompatible. Restore only
while services are stopped, and preserve current state before doing so.

`hermes update` must route to the local release controller for production.
It must never pull official main, download official ZIP replacements, or use
official Electron update feeds. Development updates use the Git workflow below.
Gateway chat updates must not stop their own hosting process; use PowerShell.
Keep these safeguards when merging upstream changes to any update entry point.

## Upstream synchronization

`origin` is `https://github.com/mirzaahmergull/Hermes-Ahmer.git`.
`upstream` is `https://github.com/NousResearch/hermes-agent.git`.
On request (typically monthly), fetch upstream main, merge into the fork on
a review branch, retain Ahmer's commits, resolve conflicts and test meaningful
contracts. Push the integrated fork after verification. Never reset the fork
to upstream or force-push away personal commits. Upstream sync does not deploy.
Build and promote a chosen integrated commit separately.

## Current personal fixes

Managed Windows gateway dependency bootstrap and strict live-process detection;
Windows command-line argument boundaries; Slack native Working status uses
Agent Sessions lifecycle values processing/active. Preserve corresponding tests.
Alibaba/DashScope credentials have been removed from user configuration; do not
reintroduce credentials or restore old env/auth backups without user intent.

## Verification and reporting

Use the canonical test runner and isolated homes. Verify candidate CLI/TUI/web,
update routing, production paths, gateway, Slack connection, skill inventory,
config/auth preservation, and SQLite health. Native UI and real Slack message
delivery require actual end-to-end evidence; do not label mocks as live proof.
Log commit IDs and test outcomes without secrets. Never promise a backup restore
will preserve messages received after that backup.
