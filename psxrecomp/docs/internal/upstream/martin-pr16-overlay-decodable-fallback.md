# PR #16 decodable overlay fallback provenance

This branch isolates the reusable discovery fallback from Martin Penkava's
[`mstan/psxrecomp` PR #16](https://github.com/mstan/psxrecomp/pull/16), exact
source commit
[`e6809ccf7d778a4c2f32d9e27c0ec31a44cbd2ba`](https://github.com/mstan/psxrecomp/commit/e6809ccf7d778a4c2f32d9e27c0ec31a44cbd2ba).

Last evaluated: 2026-07-14

| Item | Value |
| --- | --- |
| Head repository/branch | `shaneomac1337/psxrecomp`, `smackdown2-fixes` |
| Pull request/source commit | `mstan/psxrecomp` PR #16, `e6809ccf7d778a4c2f32d9e27c0ec31a44cbd2ba` |
| Local base | `7085721afe338a03cb114321a3576cdff420b732` (`origin/master`) |
| Local branch | `feat/pr16-overlay-decodable-fallback-mpenkava` |

The fallback handles executable RAM populated by bulk host transfers that do
not traverse ordinary RAM write hooks. A control transfer above the configured
boot-EXE text end is admitted only when its first word passes the existing MIPS
decoder check; the interpreter then marks that word executable. Invalid, data,
out-of-RAM, and below-floor targets remain rejected.

The source commit also added pre-initialization guards to the overlay loader.
Those guards were reviewed and merged separately in PR #23 and are explicitly
excluded here. The source commit's game name, disc ID, addresses, and validation
claims are evidence only and are not embedded in framework code.

Source authorship is retained with:

```text
Co-authored-by: Martin Penkava <mpenkava1337@gmail.com>
Co-authored-by: Claude Fable 5 <noreply@anthropic.com>
```
