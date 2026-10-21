/*
 * Tekken 3 true-widescreen activation.
 *
 * Guarded visibility-angle alternatives reveal the original stage sections
 * without changing the section grid or writing guest code pages. This static
 * plugin selects native 16:9 before renderer initialization. Disabled, both
 * the renderer and the guest visibility cone remain exact 4:3.
 */
#include "mod_plugins.h"

static void tekken3_true_widescreen_activate(void)
{
    (void)psx_mod_set_fixed_display_aspect(16u, 9u);
}

PSX_MOD_CONSTRUCTOR(tekken3_register_visual_plugins)
{
    (void)psx_mod_register_activation_plugin(
        "tekken3.true-widescreen", tekken3_true_widescreen_activate);
}
