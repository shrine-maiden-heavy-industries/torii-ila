<!-- markdownlint-disable MD024 -->
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
Unreleased template stuff

## [Unreleased]
### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security
-->

## [Unreleased]

> [!IMPORTANT]
> The minimum Python version for Torii and Torii ILA is now 3.11

### Added

- `ILABackhaulInterface.update` to allow for large multi-sample-buffer ILA dumps

### Changed

- UART ILA output is now rCOBS encoded with `0x00` end-of-frame indicators for re-syncing serial streams.
- USB ILA VID:PID changed from `04A0:ACA7` to `1D50:6190`.
- UART ILA now has an RX line and no longer sends the stream of ILA data right away after capture completion
- Bumped minimum [Torii] version to `v0.8.0`
- Bumped minimum [Torii-USB] version to `v0.8.0`
- Bumped minimum [Torii-Boards] version to `v0.8.0`
- Switched from using the old setuptools `setup.py` over to setuptools via `pyproject.toml`
- Fixed how the USB and Serial ILAs are exported when appropriate deps are installed
- Changed how UART Backhaul is instantiated

### Fixed

- Fixed missing or incomplete documentation

## [v0.1.0] - 2025-01-30

This is the first beta release of the Torii ILA module. It's not fully stable but it works
enough to have it's tires kicked.

### Added

- Simple Integrated Logic Analyzer Torii module `torii_ila.ila.IntegratedLogicAnalyzer`
- Simple Stream ILA Torii module `torii_ila.ila.StreamILA`
- UART-Based ILA and backhaul interface `torii_ila.uart`
- USB-Based ILA and backhaul interface `torii_ila.usb`
- UART and USB ILA examples

[Unreleased]: https://github.com/shrine-maiden-heavy-industries/torii-ila/compare/v0.1.0...main
[v0.1.0]: https://github.com/shrine-maiden-heavy-industries/torii-ila/compare/aa8b192...v0.1.0

[Torii]: https://github.com/shrine-maiden-heavy-industries/torii-hdl
[Torii-USB]: https://github.com/shrine-maiden-heavy-industries/torii-usb
[Torii-Boards]: https://github.com/shrine-maiden-heavy-industries/torii-boards
