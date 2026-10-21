#ifndef TEKKEN3_LAUNCHER_THEME_H
#define TEKKEN3_LAUNCHER_THEME_H
/* Tekken 3 for Linux - Custom Electric Cyan / Slate Theme */
static inline LauncherTheme tekken3_launcher_theme(void) {
    LauncherTheme t=launcher_theme_psx();
    t.background=lng_rgba(.058f,.065f,.080f,1);
    t.background2=t.background;
    t.panel=lng_rgba(.095f,.110f,.138f,1);
    t.panel_hovered=lng_rgba(.135f,.160f,.205f,1);
    t.control=lng_rgba(.120f,.145f,.185f,1);
    t.control_hovered=lng_rgba(.170f,.220f,.295f,1);
    t.border=lng_rgba(.220f,.280f,.380f,1);
    t.accent=lng_rgba(.00f,.72f,.95f,1);       /* Electric Cyan */
    t.accent_dim=lng_rgba(.02f,.38f,.62f,1);   /* Deep Sapphire */
    t.accent2=lng_rgba(.28f,.82f,.98f,1);      /* Luminous Azure Glow */
    t.text=lng_rgba(.95f,.97f,1.00f,1);        /* Crisp Ice White */
    t.text_muted=lng_rgba(.56f,.64f,.75f,1);   /* Cool Slate Mist */
    t.good=lng_rgba(.20f,.88f,.55f,1);         /* Neon Emerald */
    t.warn=lng_rgba(1.00f,.70f,.20f,1);        /* Electric Amber */
    t.focus_ring=t.accent;
    t.radius_sm=3;t.radius_lg=5;t.scanlines=0;
    t.font_body=17;t.spacing_lg=20;t.spacing_md=12;t.spacing_sm=7;
    return t;
}
#endif
