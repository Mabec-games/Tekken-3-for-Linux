#ifndef TEKKEN3_JUN_STAGE_H
#define TEKKEN3_JUN_STAGE_H
#include "psx_runtime.h"
enum { JUN_STAGE_ID = 20, JUN_STAGE_MUSIC = 16 };
unsigned tekken3_jun_stage_initialize(void);
void tekken3_jun_stage_tick(void);
int tekken3_jun_stage_prepare(const char *site);
int tekken3_jun_stage_load(CPUState *cpu);
#endif
