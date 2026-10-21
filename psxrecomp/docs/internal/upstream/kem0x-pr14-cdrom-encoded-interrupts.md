# kem0x PR 14: encoded CD-ROM interrupt matching

Evaluated and adapted on 2026-07-13.

## Provenance

The CD-ROM interrupt mask fix was rebuilt from Kareem Olim's
[PSXrecomp PR 14](https://github.com/mstan/psxrecomp/pull/14), specifically
commit
[`dd9e5c65073dd41fbac2d965d2f945a866ec59e2`](https://github.com/mstan/psxrecomp/commit/dd9e5c65073dd41fbac2d965d2f945a866ec59e2)
(`Deliver encoded CD interrupt reasons correctly`). The implementation here
centralizes the mask/status comparison in a tested internal helper rather than
copying the source patch verbatim.

The behavior follows the
[PSX-SPX CD-ROM register documentation](https://psx-spx.consoledev.net/cdromdrive/#0x1f801803-read-banks-1-and-3-hintsts):
HINTSTS bits 0..2 are an encoded HC05 interrupt reason, but the interrupt line
is asserted whenever `HINTMSK & HINTSTS` is nonzero. Converting the reason to a
one-hot bit before applying the mask is therefore incorrect. A common `0x07`
mask must deliver encoded INT4 (DataEnd) and INT5 (DiskError) as well as
INT1--INT3.

## Deliberately excluded

This branch does not import PR 14's WebAssembly/web frontend, Pepsiman-specific
hooks or patches, CD-DA playback changes, SPU changes, raster/rendering changes,
or any other runtime and build-system material. Those changes have different
scope and review requirements and are not needed for encoded interrupt mask
matching.
