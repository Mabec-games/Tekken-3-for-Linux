# Release contents and reporting

Public setup packages contain the setup launcher, compiler SDK, source, authored
mod textures and gallery artwork. The game disc, retail BIOS, imported Jun data,
generated retail code, saves, developer captures and local settings are excluded.

Release builds disable the TCP debug server and debug tools. Development
configurations can enable them; use those only for local testing. Netplay is
disabled in this preview. The easy setup launcher downloads a pinned compiler toolchain and MAME from
their upstream releases, checks archive SHA-256 hashes, and keeps tools inside
the application folder. The Jun importer uses local game data. Cancel closes
the Windows process group containing setup, MAME and compiler processes.

Do not upload ROMs, BIOS files, imported packs, memory cards or raw memory captures
with bug reports. Review logs before posting: locally generated logs can contain
your filesystem paths. Report security problems privately through GitHub's
security reporting feature when available.

Release checks include an explicit file allowlist, credential/private-key pattern
scan, personal-path checks, a Windows Defender scan and archive SHA-256 hashes.
These checks are not a guarantee that software has no vulnerabilities.
