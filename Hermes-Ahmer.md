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
- The controller has its own pinned Python in `C:\Hermes-Ahmer\controller-runtime`;
  production does not depend on the developer checkout or the old installation.
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
The stable build command refreshes changed release-controller code from the
clean, committed development checkout first. `ahmer-release controller` does
that explicitly without building or deploying. Rollback keeps this controller's
update safeguards while selecting the prior runtime.

The build also packages the light desktop app and binds its backend to the
selected contained release. Its existing Roaming\\Hermes profile and app identity
stay unchanged. The Start Menu shortcut follows the stable production launcher.
Pinned tools are cached under Hermes-Ahmer-builds\\cache and validated by PM
against the selected commit's lock; caches are never user configuration.
`scripts/ahmer/features.json` records the production extras carried by the
existing installation, including Slack, computer use, web, voice and Google.
Personal builds explicitly select this set instead of compiling every optional
upstream integration. SILK was not installed and is not part of this baseline;
adding it requires a compatible wheel or C++ compiler. Expand this file before
building when adding capabilities, and verify their imports in the candidate.

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
Windows startup exposure must respect the external install stamp and leave the
controller-owned default-home launchers intact. Per-release launcher repair
must not bypass desktop routing, active selection or credential sanitization.

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

An existing Windows access denial prevents reading the legacy default-home
`pending_messages` directory. Leave it and its ACL intact. The controller records
this exact exception in `preserved-in-place.json`; it copies the rest of the
accessible home and never deletes the unreadable directory during restoration.
Do not describe this directory as backed up or its contents as verified.
Restore the five primary databases through SQLite's backup API; do not copy
raw WAL/SHM sidecars over mapped files. Close integrity-check connections before
switching or restoring state. The controller explicitly uses UTF-8 output even
under isolated Windows Python, so printing status cannot cause false recovery.
