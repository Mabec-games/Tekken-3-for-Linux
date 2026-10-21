#pragma once
#ifdef __cplusplus
extern "C" {
#endif
int tekken3_main_menu_quit_requested(void);
/* Called before the native menu prologue in every execution backend.
 * Nonzero means Quit was consumed; caller returns to the guest link register. */
int tekken3_main_menu_enter(void);
#ifdef __cplusplus
}
#endif
