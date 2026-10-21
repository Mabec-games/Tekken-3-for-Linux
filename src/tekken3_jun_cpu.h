/* SLUS-00402 CPU support. Included after the roster's guarded patch/copy
 * helpers; the offline harness exercises these same patches on disc code. */
#ifndef TEKKEN3_JUN_CPU_H
#define TEKKEN3_JUN_CPU_H

static void jun_cpu_initialize(uint32_t profiles) {
    /* Character-specific spacing/response parameters, not move IDs or combos.
     * Difficulty still comes from the native 3 x 10 tuning profiles. */
    copy_guest(profiles,0x80098260,22*12);
    copy_guest(profiles+22*12,0x80098260+9*12,12);
    copy_guest(profiles+23*12,0x80098260+9*12,12);
}

static void jun_cpu_patch(uint32_t profiles) {
    /* Both the CPU's and its opponent's IDs index this table. */
    patch(0x800616cc,0x3c04800a,0x3c040000|(profiles>>16));
    patch(0x800616d4,0x24848260,0x34840000|(profiles&65535));

    /* BNS record 0: reset the extended per-run counters when starting a
     * new Team Battle or Survival run. Each array fits in the existing
     * mode union (Team ends at +A3, Survival at +8F; Arcade uses +90..BC).
     * Never change the value 22 used as the empty-selection sentinel. */
    if(psx_mod_read_word(0x800ca4d0)==0xa4600074 &&
       psx_mod_read_word(0x800ca5a4)==0xa4800060 &&
       psx_mod_read_word(0x800ca5b8)==0x24030016) {
        patch(0x800ca490,0x24100015,0x24100017);
        patch(0x800ca494,0x2623002a,0x2623002e);
        patch(0x800ca544,0x24100015,0x24100017);
        patch(0x800ca548,0x2624002a,0x2624002e);
    }

    /* BNS record 5, NOT the Tekken Force overlay at the same addresses.
     * Keep all original exclusions, unlocked-fighter filtering, RNG,
     * anti-repeat weighting and fixed Arcade bosses. Only add bit 23. */
    if(psx_mod_read_word(0x800b1fcc)!=0x27bdffb0 ||
       psx_mod_read_word(0x800b225c)!=0x27bdff00 ||
       psx_mod_read_word(0x800b26d0)!=0x27bdff30)return;
    patch(0x800b2030,0x3c03001f,0x3c03009f); /* Arcade */
    patch(0x800b2034,0x3c020015,0x3c020095); /* Time Attack */
    patch(0x800b20bc,0x28620016,0x28620018);
    patch(0x800b2164,0x28620016,0x28620018);
    patch(0x800b2268,0x3c02001f,0x3c02009f); /* Team Battle */
    patch(0x800b2344,0x2a020016,0x2a020018);
    patch(0x800b23e4,0x28620016,0x28620018);
    patch(0x800b24c0,0x28620016,0x28620018);
    patch(0x800b2574,0x28620016,0x28620018);
    /* Fold the native 0x157fff intersection into the three tier masks,
     * then OR Jun into the result before recent-opponent exclusions.
     * This stays entirely in the loaded overlay: Expansion 1 allocations
     * are DATA at 0x9F..., outside a MIPS J's 0x8... target segment.
     * Native pools: 0x3ff, 0xfbfff & 0x157fff, 0x1fffff & 0x157fff. */
    patch(0x800b26f8,0x3c08001f,0x3c080015);
    patch(0x800b2704,0x3508ffff,0x35087fff);
    patch(0x800b2708,0x3c08000f,0x3c080005);
    patch(0x800b270c,0x3508bfff,0x35083fff);
    patch(0x800b2710,0x3c020015,0x3c020080);
    patch(0x800b2714,0x34427fff,0x00000000);
    patch(0x800b2718,0x01024024,0x01024025);
    patch(0x800b2798,0x28620016,0x28620018); /* Survival candidates */
    patch(0x800b16c8,0x28a20016,0x28a20018); /* Survival totals */
}
#endif
