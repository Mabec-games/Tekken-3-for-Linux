#pragma once
/* Verified private TTT1 ARC members; see tools/data/jun_costumes.json.
 * Generated metadata only. No ROM content is embedded in this header. */
enum { JUN_COSTUME_COUNT=3 };
typedef struct {
    unsigned model_size, texture_size, relocation_count;
    const char *model_sha, *texture_sha, *relocation_sha;
} JunCostumeSpec;
static const JunCostumeSpec jun_costume_specs[JUN_COSTUME_COUNT]={
    {44732,39492,168,"c436fbe39bbc98acf24e72a9919812253e95f948ce7a0cd500f9d3f50ef10ddc","72aadb81c2cfd43368185180d408ebde13a9f0d8b0456a35279c957919179877","d7590230c1176e07dc5d5f784722cc0c9b8b8fb8ebe5b2c415338b270a6ccd7b"},
    {44436,40612,164,"2d3dc1048cfea45d221acec0d0b11adb64b73b6b32ff3e3e5443bdf92b309da2","299207c9e287afc29248538226c0dd41b023bb647a8e200cfd3463ef4df603eb","63b90410ac834a3234c416d0cc0a6ac29fca582e4c8f523d3a6adb54d8d31277"},
    {47740,38788,172,"6c269a9aa6c9bcd7d4ced67e73647fba4aa1b20b3c9c6abc4d67caac2c0c2c0b","9f289c52062a521da1111a04ae4abbb0f06a7ec0c5eda5ea97f4db4750f57f40","66dcb5d2ba015b51913055bab7e9104f7d18e18b1b29e4e7cb84d394e24f8e72"},
};
