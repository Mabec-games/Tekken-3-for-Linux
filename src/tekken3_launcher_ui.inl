/* Game-owned native frontend. Included after the shared provider-backed panels.
 * No webview, remote assets, ROM copying, or second settings format. */
enum T3Page { T3_PLAY,T3_MODS,T3_KEYBOARD,T3_CONTROLLER,T3_DISCS,T3_SETTINGS,T3_SAVES,T3_ONLINE };
static T3Page t3_page=T3_PLAY;
static tekken3::DiscLibrary t3_discs;
static std::string t3_observed_disc;
static int t3_remove_disc=-1;
static bool t3_reset_keys=false;
static LauncherTexture g_t3_logo{};

/* Tekken 3 256-Word P2P Dictionary (0..255 byte mapping) */
static const char* const kTekkenWords[256] = {
    // 00-31: Characters & Personas
    "JIN", "KAZUYA", "HEIHACHI", "PAUL", "LAW", "NINA", "ANNA", "YOSHIMITSU",
    "BRYAN", "HWOARANG", "EDDY", "KING", "LEI", "XIAOYU", "GUNJACK", "MOKUJIN",
    "OGRE", "TRUEOGRE", "PANDA", "KUMA", "JULIA", "BOSCONOVITCH", "GON", "TIGER",
    "ARMOR", "MICHELLE", "JUN", "DEVIL", "ANGEL", "BAEK", "BRUCE", "WANG",
    // 32-63: More Fighters & Allies
    "GANRYU", "KUNIMITSU", "LEE", "RAVEN", "ASUKA", "FENG", "LILI", "DRAGUNOV",
    "LARS", "ALISA", "ZAFINA", "MIGUEL", "BOB", "LEO", "STEVE", "CHRISTIE",
    "ROGER", "ALEX", "VIOLET", "SEVEN", "JACKTWO", "PROTOTYPE", "DEVILJIN", "FOREST",
    "MARSHALL", "DRB", "TETSUJIN", "UNKNOWN", "COMBOBOT", "KAZUMI", "LEROY", "FAHKUMRAM",
    // 64-95: Moves & Techniques
    "GODFIST", "EWGF", "HELLSWEEP", "DEATHFIST", "DEMOLITION", "FLAMINGO", "HUNTING", "WINDMILL",
    "SOMERSAULT", "DRAGON", "PHOENIX", "TIGERKICK", "SHIN", "TSUNAMI", "RAZOR", "SCREW",
    "UPPERCUT", "HOOK", "JAB", "ROUNDHOUSE", "SWEEP", "TACKLE", "THROW", "REVERSAL",
    "PARRY", "LOWPARRY", "SIDESTEP", "BACKDASH", "WAVEDASH", "CROUCH", "COUNTER", "PUNISH",
    // 96-127: Combat Mechanics & System
    "LAUNCHER", "JUGGLE", "COMBO", "BOUND", "WALLSPLAT", "FLOORBREAK", "BALCONY", "TECHROLL",
    "UKEMI", "BLOCK", "CRUSH", "FRAME", "ADVANTAGE", "RECOVERY", "CHIP", "GUARD",
    "RAGE", "HEAT", "DRIVE", "RAGEDRIVE", "RAGEART", "SPARK", "IMPACT", "SMASH",
    "BLAST", "STRIKE", "VOLTAGE", "THUNDER", "LIGHTNING", "AURA", "FIRE", "SHADOW",
    // 128-159: Stages & Locations
    "TEMPLE", "HIGHLAND", "TRESTLE", "STREET", "CARNIVAL", "LAB", "BEACH", "CAVE",
    "TAISHI", "DOJO", "SKYSHRINE", "MANOR", "SEWERS", "ARENA", "STADIUM", "HELIPAD",
    "ROOFTOP", "GARDEN", "VOLCANO", "PALACE", "ISLAND", "SHRINE", "AIRPORT", "METROPOLIS",
    "CEMETERY", "CASINO", "CASTLE", "CITADEL", "CATHEDRAL", "COLOSSEUM", "HARBOR", "SUBWAY",
    // 160-191: Tournament & Lore
    "MISHIMA", "ZAIBATSU", "GCORP", "TOURNAMENT", "IRONFIST", "CHAMPION", "TROPHY", "TEKKEN",
    "FORCE", "CHICKEN", "GREAT", "PERFECT", "VICTORY", "DEFEAT", "KNOCKOUT", "DRAW",
    "ROUND", "FIGHT", "READY", "ARCADE", "PRACTICE", "SURVIVAL", "TIMETRIAL", "TEAMBATTLE",
    "BALL", "THEATRE", "RECORD", "GHOST", "BADGE", "EMBLEM", "DESTINY", "BLOODLINE",
    // 192-223: Gear, Attire & Visuals
    "GLOVES", "BELT", "GI", "SASH", "HEADBAND", "MASK", "CAPE", "BOOTS",
    "BLADE", "SWORD", "DAGGER", "KATANA", "NUNCHAKU", "STAFF", "ROBOT", "CYBORG",
    "GENE", "DEVILGENE", "TATTOO", "WINGS", "HORNS", "TAIL", "FANGS", "CLAWS",
    "CHAINS", "ARMORCLAD", "JACKET", "PANTS", "VEST", "BANDAGE", "EYEPATCH", "SHADES",
    // 224-255: Iconic Sounds, States & Flavor
    "DORYA", "DEYA", "SEI", "CHESTO", "KWO", "WAH", "COMEON", "EXCELLENT",
    "CHALLENGER", "WARNING", "DANGER", "FATAL", "CRITICAL", "COUNTERHIT", "CLEANHIT", "MAXIMUM",
    "SPEED", "POWER", "FURY", "WRATH", "JUSTICE", "CHAOS", "ORDER", "LEGEND",
    "WARRIOR", "MASTER", "BRAWLER", "FIGHTER", "SLAYER", "CONQUEROR", "OVERLORD", "GOD"
};

static int t3_word_to_byte(const std::string& token) {
    for (int i = 0; i < 256; ++i) {
        if (strcasecmp(token.c_str(), kTekkenWords[i]) == 0) {
            return i;
        }
    }
    return -1;
}

static uint8_t p2p_session_salt = (uint8_t)(time(nullptr) ^ 0x5A);

static std::string t3_encode_ip(const std::string& ip_str, int port = 7777) {
    int b[4];
    char extra = 0;
    if (sscanf(ip_str.c_str(), "%d.%d.%d.%d%c", &b[0], &b[1], &b[2], &b[3], &extra) != 4) {
        return "";
    }
    for (int i = 0; i < 4; ++i) {
        if (b[i] < 0 || b[i] > 255) return "";
    }
    uint8_t s = p2p_session_salt;
    uint8_t w[4];
    for (int i = 0; i < 4; ++i) {
        uint8_t k = (uint8_t)(s * 37 + 101 + i * 29);
        w[i] = (uint8_t)b[i] ^ k;
    }
    std::string code = std::string(kTekkenWords[s]) + "-" +
                       kTekkenWords[w[0]] + "-" +
                       kTekkenWords[w[1]] + "-" +
                       kTekkenWords[w[2]] + "-" +
                       kTekkenWords[w[3]];
    if (port != 7777 && port > 0 && port <= 65535) {
        code += ":" + std::to_string(port);
    }
    return code;
}

static bool t3_decode_code(const std::string& input, std::string& out_endpoint, bool* is_word_code = nullptr) {
    out_endpoint.clear();
    if (is_word_code) *is_word_code = false;

    size_t start = input.find_first_not_of(" \t\r\n");
    if (start == std::string::npos) return false;
    size_t end = input.find_last_not_of(" \t\r\n");
    std::string trimmed = input.substr(start, end - start + 1);

    int port = 7777;
    size_t colon_pos = trimmed.find(':');
    std::string main_part = trimmed;
    if (colon_pos != std::string::npos) {
        std::string port_str = trimmed.substr(colon_pos + 1);
        main_part = trimmed.substr(0, colon_pos);
        try {
            port = std::stoi(port_str);
            if (port <= 0 || port > 65535) return false;
        } catch (...) {
            return false;
        }
    }

    std::vector<std::string> tokens;
    std::string current;
    for (char c : main_part) {
        if (c == '-' || c == '_' || c == ' ' || c == '.' || c == '/') {
            if (!current.empty()) {
                tokens.push_back(current);
                current.clear();
            }
        } else {
            current.push_back(c);
        }
    }
    if (!current.empty()) tokens.push_back(current);

    // 1. Salted 5-word code: SALT-W1-W2-W3-W4
    if (tokens.size() == 5) {
        int w[5];
        bool all_words = true;
        for (int i = 0; i < 5; ++i) {
            w[i] = t3_word_to_byte(tokens[i]);
            if (w[i] < 0) { all_words = false; break; }
        }
        if (all_words) {
            uint8_t s = (uint8_t)w[0];
            int b[4];
            for (int i = 0; i < 4; ++i) {
                uint8_t k = (uint8_t)(s * 37 + 101 + i * 29);
                b[i] = (uint8_t)w[i + 1] ^ k;
            }
            out_endpoint = std::to_string(b[0]) + "." +
                           std::to_string(b[1]) + "." +
                           std::to_string(b[2]) + "." +
                           std::to_string(b[3]) + ":" +
                           std::to_string(port);
            if (is_word_code) *is_word_code = true;
            return true;
        }
        // Fallback: 4-word code with explicit numeric port suffix (e.g. W1-W2-W3-W4-7777)
        if (colon_pos == std::string::npos) {
            int bytes[4];
            bool four_words = true;
            for (int i = 0; i < 4; ++i) {
                bytes[i] = t3_word_to_byte(tokens[i]);
                if (bytes[i] < 0) { four_words = false; break; }
            }
            if (four_words) {
                try {
                    int p = std::stoi(tokens[4]);
                    if (p > 0 && p <= 65535) {
                        out_endpoint = std::to_string(bytes[0]) + "." +
                                       std::to_string(bytes[1]) + "." +
                                       std::to_string(bytes[2]) + "." +
                                       std::to_string(bytes[3]) + ":" +
                                       std::to_string(p);
                        if (is_word_code) *is_word_code = true;
                        return true;
                    }
                } catch (...) {}
            }
        }
    }

    // 2. Legacy direct 4-word code: W0-W1-W2-W3
    if (tokens.size() == 4) {
        int bytes[4];
        bool all_words = true;
        for (int i = 0; i < 4; ++i) {
            bytes[i] = t3_word_to_byte(tokens[i]);
            if (bytes[i] < 0) { all_words = false; break; }
        }
        if (all_words) {
            out_endpoint = std::to_string(bytes[0]) + "." +
                           std::to_string(bytes[1]) + "." +
                           std::to_string(bytes[2]) + "." +
                           std::to_string(bytes[3]) + ":" +
                           std::to_string(port);
            if (is_word_code) *is_word_code = true;
            return true;
        }
    }

    int ip[4];
    if (sscanf(main_part.c_str(), "%d.%d.%d.%d", &ip[0], &ip[1], &ip[2], &ip[3]) == 4) {
        bool valid_ip = true;
        for (int i = 0; i < 4; ++i) {
            if (ip[i] < 0 || ip[i] > 255) { valid_ip = false; break; }
        }
        if (valid_ip) {
            out_endpoint = std::to_string(ip[0]) + "." +
                           std::to_string(ip[1]) + "." +
                           std::to_string(ip[2]) + "." +
                           std::to_string(ip[3]) + ":" +
                           std::to_string(port);
            return true;
        }
    }

    if (strcasecmp(main_part.c_str(), "localhost") == 0) {
        out_endpoint = "127.0.0.1:" + std::to_string(port);
        return true;
    }

    return false;
}

/* Public IP Auto-Detection (Asynchronous) */
static std::string g_public_ip;
static std::mutex g_public_ip_mtx;
static std::atomic<bool> g_fetching_public_ip{false};
static std::atomic<bool> g_public_ip_failed{false};

static void t3_fetch_public_ip_async(bool force = false) {
    if (g_fetching_public_ip.load()) return;
    {
        std::lock_guard<std::mutex> lock(g_public_ip_mtx);
        if (!g_public_ip.empty() && !force) return;
    }
    g_fetching_public_ip.store(true);
    g_public_ip_failed.store(false);

    std::thread([]() {
        FILE* fp = popen("curl -s --max-time 3 https://api.ipify.org 2>/dev/null || curl -s --max-time 3 https://checkip.amazonaws.com 2>/dev/null", "r");
        std::string result;
        if (fp) {
            char buf[64] = {0};
            if (fgets(buf, sizeof(buf) - 1, fp)) {
                std::string s(buf);
                size_t start = s.find_first_not_of(" \t\r\n");
                size_t end = s.find_last_not_of(" \t\r\n");
                if (start != std::string::npos && end != std::string::npos) {
                    s = s.substr(start, end - start + 1);
                    int b[4];
                    if (sscanf(s.c_str(), "%d.%d.%d.%d", &b[0], &b[1], &b[2], &b[3]) == 4) {
                        if (b[0]>=0&&b[0]<=255 && b[1]>=0&&b[1]<=255 && b[2]>=0&&b[2]<=255 && b[3]>=0&&b[3]<=255) {
                            result = s;
                        }
                    }
                }
            }
            pclose(fp);
        }

        {
            std::lock_guard<std::mutex> lock(g_public_ip_mtx);
            if (!result.empty()) {
                g_public_ip = result;
            } else {
                g_public_ip_failed.store(true);
            }
        }
        g_fetching_public_ip.store(false);
    }).detach();
}

/* P2P Netplay State */
static int p2p_mode = 0; // 0 = Host (P1), 1 = Join (P2)
static int p2p_host_port = 7777;
static char p2p_join_input[128] = "";
static char p2p_join_peer[64] = "";
static int p2p_join_local_port = 0; // 0 = automatic / ephemeral
static int p2p_delay = 2; // default 2 frames
static int p2p_session_id = 1;
static char p2p_status_msg[128] = "";
static bool p2p_join_valid = false;
static bool p2p_join_is_code = false;
static double p2p_copy_toast_timer = 0.0;
static std::string p2p_copy_toast_msg = "";

static const char* const kT3AspectLabels[2] = {
    "4:3 (Native)",
    "16:9 (Widescreen)"
};

static bool t3_is_widescreen_mod_enabled(const LauncherModel* m) {
    if (!m || !m->mods || !m->mods->feature_count || !m->mods->feature_get)
        return m ? (m->s.aspect_index == 1) : false;
    const int n = m->mods->feature_count(m->mods->ctx);
    for (int i = 0; i < n; ++i) {
        RecompLauncherCModFeature f{};
        if (m->mods->feature_get(m->mods->ctx, i, &f)) {
            if (std::strcmp(f.package_id, "tekken3.enhancement.true-widescreen") == 0 &&
                std::strcmp(f.id, "true-widescreen") == 0) {
                return f.enabled != 0;
            }
        }
    }
    return m->s.aspect_index == 1;
}

static void t3_set_widescreen_mod_enabled(LauncherModel* m, bool enabled) {
    if (!m) return;
    m->s.aspect_index = enabled ? 1 : 0;
    m->s.widescreen = enabled ? 1 : 0;
    if (m->mods && m->mods->feature_enable) {
        m->mods->feature_enable(m->mods->ctx,
                                "tekken3.enhancement.true-widescreen",
                                "true-widescreen",
                                enabled ? 1 : 0);
    }
}

static void tekken3_launcher_init(LauncherModel* m) {
    t3_page=T3_PLAY;t3_remove_disc=-1;t3_reset_keys=false;
    m->netplay_supported = true;
    m->aspect_mask = 0x3;
    m->aspect_labels = kT3AspectLabels;
    m->num_aspect_labels = 2;
    m->aspect_experimental = false;
    m->s.aspect_index = t3_is_widescreen_mod_enabled(m) ? 1 : 0;
    m->s.widescreen = m->s.aspect_index;
    t3_fetch_public_ip_async();
    if(!g_t3_logo.id) {
        g_t3_logo=launcher_texture_load(asset("assets/img/t3.png").c_str());
        if(!g_t3_logo.id)
            g_t3_logo=launcher_texture_load(asset("assets/img/brand_mark.tga").c_str());
    }
    t3_discs.load(std::filesystem::u8path(asset("disc-library.txt")));
    if(t3_discs.error.empty() && t3_discs.has_selection && !tekken3_launcher_disc_is_explicit)
        launcher_model_set_rom(m,t3_discs.selected.c_str());
    t3_observed_disc=m->rom_full;
    if(t3_discs.error.empty() && m->rom_full[0]) {
        t3_discs.attach(m->rom_full);t3_discs.selected=tekken3::DiscLibrary::normalize(m->rom_full);t3_discs.save();
    }
    m->s.skip_launcher=0;
}
static void t3_goto(LauncherModel* m,T3Page page) {
    launcher_model_cancel_capture(m);launcher_model_cancel_hk_capture(m);
    launcher_model_cancel_camera_capture(m);
    m->map_all_active=false;m->map_all_wait_release=false;
    t3_page=page;
    launcher_model_set_view(m,page==T3_MODS?LNG_VIEW_MODS:
        page==T3_SETTINGS?LNG_VIEW_SETTINGS:
        (page==T3_KEYBOARD || page==T3_CONTROLLER)?LNG_VIEW_CONTROLLER:LNG_VIEW_DASHBOARD);
    if(page==T3_DISCS)t3_discs.refresh();
    if(page==T3_ONLINE) {
        t3_fetch_public_ip_async();
        np_refresh_host_ip(m);
    }
}
static void t3_heading(const char* text) {
    ImGui::PushFont(g_t3_heading);ImGui::TextUnformatted(text);ImGui::PopFont();
}
static bool t3_compatible(const LauncherModel* m) {
    std::string serial;
    for(const char* p=m->verify.serial;*p;p++)
        if(std::isalnum((unsigned char)*p))serial+=(char)std::toupper((unsigned char)*p);
    return serial=="SLUS00402";
}
static void t3_disc_status(LauncherModel* m,const LauncherTheme& th) {
    if(!m->rom_full[0])ImGui::TextColored(col(th.warn),"NO DISC SELECTED");
    else if(!m->rom_present || m->verify.verdict==3 || m->verify.verdict==0)
        ImGui::TextColored(col(th.warn),"DISC NOT READY - check the image and its tracks");
    else if(!t3_compatible(m))ImGui::TextColored(col(th.warn),"INCOMPATIBLE DISC - this build requires Tekken 3 USA");
    else ImGui::TextColored(col(th.good),"DISC READY  /  %s  /  %s",m->verify.serial,m->verify.region);
}
static void t3_pick_disc(LauncherModel* m) {
    static const char* patterns[]={"*.cue","*.bin","*.iso","*.chd"};
    request_rom_picker(m,"Attach a disc image",patterns,4,"PlayStation disc images",false);
}
static void t3_player_selector(LauncherModel* m) {
    for(int p=0;p<2;p++) {
        if(p)ImGui::SameLine();
        const bool selected=m->cfg_player==p;
        if(selected)ImGui::PushStyleColor(ImGuiCol_Button,col(g_th->accent_dim));
        if(ImGui::Button(p?"PLAYER 2":"PLAYER 1",ImVec2(126,34))) {
            launcher_model_cancel_capture(m);m->map_all_active=false;m->cfg_player=p;
            launcher_binds_refresh(m);
        }
        if(selected)ImGui::PopStyleColor();
    }
    ImGui::Spacing();
}
static const char* t3_move_label(const char* button) {
    if(!strcmp(button,"Square"))return "1  /  Left punch";
    if(!strcmp(button,"Triangle"))return "2  /  Right punch";
    if(!strcmp(button,"Cross"))return "3  /  Left kick";
    if(!strcmp(button,"Circle"))return "4  /  Right kick";
    if(!strcmp(button,"Start"))return "Pause / confirm";
    return "";
}
static void t3_keyboard(LauncherModel* m,const LauncherTheme& th) {
    t3_heading("KEYBOARD MAPPING");
    ImGui::TextColored(col(th.text_muted),"Keys and controller buttons are stored separately.");
    ImGui::TextWrapped("Each player uses only their assigned input device. P2 keyboard defaults: I/J/K/L movement, numpad 1/2/4/5 attacks, U/O shoulders.");
    ImGui::Spacing();t3_player_selector(m);
    const int p=m->cfg_player;
    ImGui::Text("Active input: %s",launcher_model_player_src_label(m,p));
    if(m->s.player_src[p]!=1) {
        ImGui::SameLine();
        if(ImGui::Button("Use keyboard for this player"))
            launcher_model_set_source(m,p,1,0,nullptr,nullptr);
    }
    ImGui::TextColored(col(th.text_muted),"Select a binding, then press a key. Esc cancels; Clear removes that binding.");
    ImGui::Spacing();
    const auto* prof=(const SystemProfile*)m->profile;
    const float height=std::max(160.0f,ImGui::GetContentRegionAvail().y-62);
    if(ImGui::BeginTable("keyboard-map",4,ImGuiTableFlags_RowBg|ImGuiTableFlags_BordersInnerH|
            ImGuiTableFlags_ScrollY|ImGuiTableFlags_SizingStretchProp,ImVec2(0,height))) {
        ImGui::TableSetupColumn("PS1 INPUT",ImGuiTableColumnFlags_WidthFixed,130);
        ImGui::TableSetupColumn("TEKKEN",ImGuiTableColumnFlags_WidthFixed,158);
        ImGui::TableSetupColumn("PRIMARY KEY");ImGui::TableSetupColumn("ALTERNATE KEY");
        ImGui::TableSetupScrollFreeze(0,1);ImGui::TableHeadersRow();
        for(int b=0;b<prof->controller.button_count && b<LNG_MAX_BUTTONS;b++) {
            ImGui::PushID(b);ImGui::TableNextRow();ImGui::TableNextColumn();
            ImGui::AlignTextToFramePadding();ImGui::TextUnformatted(prof->controller.buttons[b].label);
            ImGui::TableNextColumn();ImGui::AlignTextToFramePadding();
            ImGui::TextColored(col(th.text_muted),"%s",t3_move_label(prof->controller.buttons[b].label));
            for(int slot=0;slot<2;slot++) {
                ImGui::TableNextColumn();ImGui::PushID(slot);
                const bool capture=m->capturing && !m->capture_pad && m->capture_btn==b && m->capture_slot==slot;
                const char* text=capture?"PRESS A KEY...":slot?m->binds_alt[p][b]:m->binds[p][b];
                if(capture)ImGui::PushStyleColor(ImGuiCol_Button,col(th.accent_dim));
                if(ImGui::Button(text[0]?text:"Unbound",ImVec2(std::max(60.f,ImGui::GetContentRegionAvail().x-66),0)))
                    launcher_model_begin_capture_slot(m,b,slot);
                if(capture)ImGui::PopStyleColor();
                ImGui::SameLine();
                if(ImGui::SmallButton("Clear"))launcher_binds_set_button_slot(m,p+1,b,slot,0);
                ImGui::PopID();
            }
            ImGui::PopID();
        }
        ImGui::EndTable();
    }
    if(ImGui::Button("Reset keyboard defaults"))t3_reset_keys=true;
    ImGui::SameLine();ImGui::TextColored(col(th.text_muted),"Bindings save as you map them.");
    if(t3_reset_keys)ImGui::OpenPopup("Reset keyboard?");
    if(ImGui::BeginPopupModal("Reset keyboard?",nullptr,ImGuiWindowFlags_AlwaysAutoResize)) {
        ImGui::Text("Reset Player %d keyboard keys? Controller profiles are unchanged.",p+1);
        if(ImGui::Button("Reset")) {launcher_binds_reset_keyboard(m,p+1);t3_reset_keys=false;ImGui::CloseCurrentPopup();}
        ImGui::SameLine();if(ImGui::Button("Cancel")){t3_reset_keys=false;ImGui::CloseCurrentPopup();}
        ImGui::EndPopup();
    }
}
static void t3_library(LauncherModel* m,const LauncherTheme& th) {
    t3_heading("DISC LIBRARY");
    ImGui::TextWrapped("Attach your own disc images. CUE files keep multi-track BIN images together. Detaching never deletes a ROM or its tracks.");
    ImGui::Spacing();
    if(ImGui::Button("+ Attach image",ImVec2(156,36)))t3_pick_disc(m);
    ImGui::SameLine();if(ImGui::Button("Recheck selected",ImVec2(166,36))) {
        std::string path=m->rom_full;launcher_model_set_rom(m,path.c_str());t3_discs.refresh();
    }
    if(m->rom_full[0] && m->verify.verdict!=1 && m->setup_wizard_supported &&
       (m->prepare_disc_cb || m->prepare_with_progress_cb)) {
        ImGui::SameLine();
        if(ImGui::Button("Image setup...",ImVec2(150,36))) {
            m->setup_wizard_open=true;m->setup_page=m->setup_needs_toolchain?0:1;
        }
    }
    ImGui::Spacing();t3_disc_status(m,th);
    if(!t3_discs.error.empty())ImGui::TextWrapped("%s",t3_discs.error.c_str());
    ImGui::Separator();ImGui::Spacing();
    if(t3_discs.entries.empty())ImGui::TextDisabled("No attached images. Use Attach image to choose your Tekken 3 disc.");
    for(size_t i=0;i<t3_discs.entries.size();i++) {
        const auto& entry=t3_discs.entries[i];const bool active=tekken3::DiscLibrary::same(entry.path,m->rom_full);
        ImGui::PushID((int)i);
        std::string name=std::filesystem::u8path(entry.path).filename().u8string();
        if(ImGui::Selectable(name.c_str(),active,0,ImVec2(0,30)))launcher_model_set_rom(m,entry.path.c_str());
        ImGui::TextColored(col(entry.present?th.text_muted:th.warn),"%s",entry.present?(active?"SELECTED":"ATTACHED"):"FILE MISSING");
        ImGui::SameLine();
        if(ImGui::SmallButton("Detach")){t3_remove_disc=(int)i;ImGui::OpenPopup("Detach image?");}
        ImGui::TextWrapped("%s",entry.path.c_str());
        if(ImGui::BeginPopupModal("Detach image?",nullptr,ImGuiWindowFlags_AlwaysAutoResize)) {
            ImGui::TextUnformatted("Remove this library reference? The disc files will stay on disk.");
            if(ImGui::Button("Detach reference")) {
                if(t3_discs.detach(i)) {
                    if(active)launcher_model_set_rom(m,t3_discs.entries.empty()?"":t3_discs.entries[0].path.c_str());
                    t3_observed_disc=m->rom_full;
                }
                t3_remove_disc=-1;ImGui::CloseCurrentPopup();
            }
            ImGui::SameLine();if(ImGui::Button("Cancel")){t3_remove_disc=-1;ImGui::CloseCurrentPopup();}
            ImGui::EndPopup();
        }
        ImGui::Separator();ImGui::PopID();
    }
    ImGui::Spacing();
    ImGui::TextColored(col(th.text_muted),"This recompilation runs Tekken 3 USA (SLUS-00402), not arbitrary PS1 games.");
}
static void t3_home(LauncherModel* m,const LauncherTheme& th) {
    /* Tekken 3 Logo displayed in Home panel */
    if(g_t3_logo.id && g_t3_logo.w>0 && ImGui::GetContentRegionAvail().x>700) {
        const float w=300,h=w*(float)g_t3_logo.h/(float)g_t3_logo.w;
        const ImVec2 pos=ImGui::GetCursorScreenPos();
        const float x=pos.x+ImGui::GetContentRegionAvail().x-w-14;
        ImGui::GetWindowDrawList()->AddImage(tid(g_t3_logo),ImVec2(x,pos.y+12),
            ImVec2(x+w,pos.y+12+h),ImVec2(0,0),ImVec2(1,1),IM_COL32(255,255,255,230));
    } else if(g_pad_digital.id && g_pad_digital.w>0 && ImGui::GetContentRegionAvail().x>790) {
        const float w=260,h=w*g_pad_digital.h/g_pad_digital.w;
        const ImVec2 pos=ImGui::GetCursorScreenPos();
        const float x=pos.x+ImGui::GetContentRegionAvail().x-w-14;
        ImGui::GetWindowDrawList()->AddImage(tid(g_pad_digital),ImVec2(x,pos.y+22),
            ImVec2(x+w,pos.y+22+h),ImVec2(0,0),ImVec2(1,1),IM_COL32(255,255,255,190));
    }
    ImGui::TextColored(col(th.accent2),"THE KING OF IRON FIST TOURNAMENT");
    ImGui::PushFont(g_t3_title);ImGui::TextUnformatted("READY TO FIGHT");ImGui::PopFont();
    ImGui::TextColored(col(th.text_muted),"Choose your setup. Launch when you're ready.");
    ImGui::Dummy(ImVec2(0,22));
    t3_heading("GAME DISC");
    if(m->rom_file[0])ImGui::TextWrapped("%s",m->rom_file);
    t3_disc_status(m,th);
    ImGui::Spacing();
    if(ImGui::Button("Manage disc images",ImVec2(205,36)))t3_goto(m,T3_DISCS);
    ImGui::Dummy(ImVec2(0,14));ImGui::Separator();ImGui::Dummy(ImVec2(0,14));
    t3_heading("PLAYER SETUP");
    for(int p=0;p<2;p++) {
        ImGui::PushID(p);ImGui::AlignTextToFramePadding();
        ImGui::Text("P%d",p+1);ImGui::SameLine(50);
        ImGui::SetNextItemWidth(std::min(300.f,ImGui::GetContentRegionAvail().x-150));
        if(ImGui::BeginCombo("##input",launcher_model_player_src_label(m,p))) {
            draw_source_selectables(m,p);ImGui::EndCombo();
        }
        ImGui::SameLine();
        if(ImGui::Button("Mapping",ImVec2(108,0))) {
            m->cfg_player=p;t3_goto(m,m->s.player_src[p]==2?T3_CONTROLLER:T3_KEYBOARD);
        }
        ImGui::PopID();
    }
    ImGui::Dummy(ImVec2(0,14));ImGui::Separator();ImGui::Dummy(ImVec2(0,14));
    t3_heading("MOD CONFIGURATION");
    int count=0,enabled=0;
    if(m->mods && m->mods->feature_count && m->mods->feature_get) {
        count=m->mods->feature_count(m->mods->ctx);
        for(int i=0;i<count;i++){RecompLauncherCModFeature f{};if(m->mods->feature_get(m->mods->ctx,i,&f) && f.enabled)enabled++;}
    }
    ImGui::Text("%d enabled / %d available features",enabled,count);
    ImGui::SameLine();if(ImGui::Button("Open mod manager"))t3_goto(m,T3_MODS);
    ImGui::TextColored(col(th.text_muted),"Review character imports, outfits and enhancements before playing.");
}
static void t3_settings(LauncherModel* m,const LauncherTheme& th) {
    t3_heading("GAME SETTINGS");
    if(ImGui::BeginTabBar("GameSettings")) {
        if(ImGui::BeginTabItem("DISPLAY")){
            ImGui::Spacing();
            const int prev_aspect = t3_is_widescreen_mod_enabled(m) ? 1 : 0;
            m->s.aspect_index = prev_aspect;
            draw_display_controls(m,th);
            if(m->s.aspect_index != prev_aspect) {
                t3_set_widescreen_mod_enabled(m, m->s.aspect_index == 1);
            }
            ImGui::EndTabItem();
        }
        if(ImGui::BeginTabItem("AUDIO")){ImGui::Spacing();draw_audio_controls(m,th);ImGui::EndTabItem();}
        if(ImGui::BeginTabItem("SYSTEM")){ImGui::Spacing();draw_system_controls(m,th);draw_input_controls(m,th);ImGui::EndTabItem();}
        if(ImGui::BeginTabItem("HOTKEYS")){ImGui::Spacing();draw_hotkeys_controls(m,th);ImGui::EndTabItem();}
        ImGui::EndTabBar();
    }
    ImGui::Spacing();
    if(launcher_model_can_restore_defaults(m) && ImGui::Button("Restore game settings defaults"))
        launcher_model_request_restore_defaults(m);
}
static void t3_p2p_netplay(LauncherModel* m,const LauncherTheme& th) {
    t3_heading("PEER-TO-PEER NETPLAY");
    ImGui::TextColored(col(th.text_muted),"Direct two-player rollback netplay over LAN or Internet using 4-word Tekken Room Codes.");
    ImGui::Spacing();

    t3_disc_status(m,th);
    if(!t3_compatible(m)) {
        ImGui::Spacing();
        ImGui::TextColored(col(th.warn),"Note: A valid Tekken 3 (USA) disc must be selected before launching Netplay.");
        if(ImGui::Button("Manage Disc Images",ImVec2(180,32))) {
            t3_goto(m,T3_DISCS);
        }
    }
    ImGui::Spacing();
    ImGui::Separator();
    ImGui::Spacing();

    // Mode Selector: HOST vs JOIN
    ImGui::TextUnformatted("SELECT ROLE:");
    ImGui::Spacing();
    {
        const bool is_host=(p2p_mode==0);
        const bool is_join=(p2p_mode==1);

        if(is_host)ImGui::PushStyleColor(ImGuiCol_Button,col(th.accent_dim));
        else ImGui::PushStyleColor(ImGuiCol_Button,col(th.control));
        if(ImGui::Button("HOST MATCH (PLAYER 1)",ImVec2(220,38))) {
            p2p_mode=0;
            p2p_status_msg[0]='\0';
            t3_fetch_public_ip_async();
            np_refresh_host_ip(m);
        }
        ImGui::PopStyleColor();

        ImGui::SameLine(0,16);

        if(is_join)ImGui::PushStyleColor(ImGuiCol_Button,col(th.accent_dim));
        else ImGui::PushStyleColor(ImGuiCol_Button,col(th.control));
        if(ImGui::Button("JOIN MATCH (PLAYER 2)",ImVec2(220,38))) {
            p2p_mode=1;
            p2p_status_msg[0]='\0';
        }
        ImGui::PopStyleColor();
    }
    ImGui::Dummy(ImVec2(0,10));

    ImGui::BeginChild("P2PSettings",ImVec2(0,-52),ImGuiChildFlags_Borders);
    ImGui::Dummy(ImVec2(0,6));

    if(p2p_mode==0) {
        ImGui::TextColored(col(th.accent),"HOST A MATCH (PLAYER 1)");
        ImGui::TextColored(col(th.text_muted),"Share your 4-word Tekken Room Code with Player 2 to connect.");
        ImGui::Dummy(ImVec2(0,10));

        std::string pub_ip;
        {
            std::lock_guard<std::mutex> lock(g_public_ip_mtx);
            pub_ip = g_public_ip;
        }

        // 1. Internet Room Code Card
        ImGui::PushStyleColor(ImGuiCol_ChildBg,ImVec4(0.12f,0.12f,0.15f,0.9f));
        ImGui::BeginChild("HostInternetCard",ImVec2(0,120),ImGuiChildFlags_Borders,ImGuiWindowFlags_NoScrollbar|ImGuiWindowFlags_NoScrollWithMouse);
        ImGui::Dummy(ImVec2(0,4));
        ImGui::Indent(12);
        ImGui::TextColored(col(th.accent),"ONLINE / INTERNET ROOM CODE:");
        ImGui::Spacing();

        if(!pub_ip.empty()) {
            std::string wan_code=t3_encode_ip(pub_ip,p2p_host_port);
            ImGui::PushFont(g_t3_heading);
            ImGui::TextColored(col(th.accent2),"%s",wan_code.c_str());
            ImGui::PopFont();
            ImGui::SameLine();
            ImGui::SetCursorPosY(ImGui::GetCursorPosY()-2);
            if(ImGui::Button("COPY CODE",ImVec2(110,30))) {
                ImGui::SetClipboardText(wan_code.c_str());
                p2p_copy_toast_msg="Internet Room Code copied to clipboard!";
                p2p_copy_toast_timer=ImGui::GetTime()+3.0;
            }
            ImGui::SameLine();
            ImGui::SetCursorPosY(ImGui::GetCursorPosY()-2);
            if(ImGui::Button("NEW CODE",ImVec2(95,30))) {
                p2p_session_salt = (uint8_t)(rand() ^ (p2p_session_salt * 37 + 101));
            }
            ImGui::Spacing();
            ImGui::TextColored(col(th.text_muted),"Share this code with Player 2. (Ensure UDP port %d is forwarded on your router)",p2p_host_port);
        } else if(g_fetching_public_ip.load()) {
            ImGui::TextColored(col(th.text_muted),"Generating Internet Room Code...");
        } else if(g_public_ip_failed.load()) {
            ImGui::TextColored(col(th.warn),"Unable to generate Internet Room Code.");
            ImGui::SameLine();
            if(ImGui::SmallButton("Retry Generation")) {
                t3_fetch_public_ip_async(true);
            }
            ImGui::Spacing();
            ImGui::TextColored(col(th.text_muted),"Check your internet connection or use the LAN Room Code below.");
        }
        ImGui::Unindent(12);
        ImGui::EndChild();
        ImGui::PopStyleColor();

        ImGui::Dummy(ImVec2(0,10));

        // 2. LAN Room Code Card
        if(m->netplay_local_address_count==0) {
            np_refresh_host_ip(m);
        }
        ImGui::PushStyleColor(ImGuiCol_ChildBg,ImVec4(0.10f,0.10f,0.12f,0.7f));
        ImGui::BeginChild("HostLanCard",ImVec2(0,120),ImGuiChildFlags_Borders,ImGuiWindowFlags_NoScrollbar|ImGuiWindowFlags_NoScrollWithMouse);
        ImGui::Dummy(ImVec2(0,4));
        ImGui::Indent(12);
        ImGui::TextColored(col(th.accent),"LOCAL NETWORK (LAN) ROOM CODE:");
        ImGui::Spacing();

        if(m->netplay_local_address_count>0) {
            const char* local_ip=m->netplay_local_addresses[0].address;
            std::string lan_code=t3_encode_ip(local_ip,p2p_host_port);
            ImGui::PushFont(g_t3_heading);
            ImGui::TextColored(col(th.text),"%s",lan_code.c_str());
            ImGui::PopFont();
            ImGui::SameLine();
            ImGui::SetCursorPosY(ImGui::GetCursorPosY()-2);
            if(ImGui::Button("COPY LAN CODE",ImVec2(130,30))) {
                ImGui::SetClipboardText(lan_code.c_str());
                p2p_copy_toast_msg="LAN Room Code copied to clipboard!";
                p2p_copy_toast_timer=ImGui::GetTime()+3.0;
            }
            ImGui::SameLine();
            ImGui::SetCursorPosY(ImGui::GetCursorPosY()-2);
            if(ImGui::Button("NEW CODE##lan",ImVec2(95,30))) {
                p2p_session_salt = (uint8_t)(rand() ^ (p2p_session_salt * 37 + 101));
            }
            ImGui::Spacing();
            ImGui::TextColored(col(th.text_muted),"For two players on the same Wi-Fi or local network router.");
        } else {
            ImGui::TextDisabled("No local network interfaces found.");
        }
        ImGui::Unindent(12);
        ImGui::EndChild();
        ImGui::PopStyleColor();

        if(ImGui::GetTime()<p2p_copy_toast_timer && !p2p_copy_toast_msg.empty()) {
            ImGui::Spacing();
            ImGui::TextColored(col(th.good),"✓ %s",p2p_copy_toast_msg.c_str());
        }

        ImGui::Dummy(ImVec2(0,10));
        ImGui::Separator();
        ImGui::Dummy(ImVec2(0,8));

        ImGui::AlignTextToFramePadding();
        ImGui::Text("Host UDP Port:");
        ImGui::SameLine(180);
        ImGui::SetNextItemWidth(120);
        ImGui::InputInt("##host_port",&p2p_host_port,0,0);
        if(p2p_host_port<1024)p2p_host_port=1024;
        if(p2p_host_port>65535)p2p_host_port=65535;

        ImGui::AlignTextToFramePadding();
        ImGui::Text("Input Delay (Frames):");
        ImGui::SameLine(180);
        ImGui::SetNextItemWidth(160);
        ImGui::SliderInt("##host_delay",&p2p_delay,1,10,"%d frames");
        ImGui::SameLine();
        ImGui::TextColored(col(th.text_muted),"(1-2 LAN / low ping, 3-4 Internet)");

        ImGui::AlignTextToFramePadding();
        ImGui::Text("Session ID:");
        ImGui::SameLine(180);
        ImGui::SetNextItemWidth(120);
        ImGui::InputInt("##host_session",&p2p_session_id,0,0);
        if(p2p_session_id<1)p2p_session_id=1;
        ImGui::SameLine();
        if(ImGui::SmallButton("Refresh Room Codes")) {
            t3_fetch_public_ip_async(true);
            np_refresh_host_ip(m);
        }

    } else {
        ImGui::TextColored(col(th.accent),"JOIN A MATCH (PLAYER 2)");
        ImGui::TextColored(col(th.text_muted),"Enter the Room Code shared by Host to connect.");
        ImGui::Dummy(ImVec2(0,10));

        ImGui::AlignTextToFramePadding();
        ImGui::Text("Room Code:");
        ImGui::SameLine(180);
        ImGui::SetNextItemWidth(340);
        ImGui::InputTextWithHint("##join_input","e.g. JIN-ASUKA-OVERLORD-ADVANTAGE-LOWPARRY",p2p_join_input,sizeof(p2p_join_input));
        ImGui::SameLine();
        if(ImGui::Button("PASTE",ImVec2(80,0))) {
            const char* clip=ImGui::GetClipboardText();
            if(clip && clip[0]) {
                strncpy(p2p_join_input,clip,sizeof(p2p_join_input)-1);
                p2p_join_input[sizeof(p2p_join_input)-1]='\0';
            }
        }
        ImGui::SameLine();
        if(ImGui::Button("CLEAR",ImVec2(70,0))) {
            p2p_join_input[0]='\0';
        }

        std::string resolved;
        bool is_code=false;
        if(p2p_join_input[0]!='\0' && t3_decode_code(p2p_join_input,resolved,&is_code)) {
            p2p_join_valid=true;
            p2p_join_is_code=is_code;
            strncpy(p2p_join_peer,resolved.c_str(),sizeof(p2p_join_peer)-1);
            p2p_join_peer[sizeof(p2p_join_peer)-1]='\0';
        } else {
            p2p_join_valid=false;
            p2p_join_peer[0]='\0';
        }

        ImGui::Dummy(ImVec2(0,4));
        ImGui::Indent(180);
        if(p2p_join_valid) {
            ImGui::TextColored(col(th.good),"✓ Room Code Verified — Ready to connect");
        } else if(p2p_join_input[0]!='\0') {
            ImGui::TextColored(col(th.warn),"✗ Unrecognized code format. Enter a valid Tekken Room Code.");
        } else {
            ImGui::TextColored(col(th.text_muted),"Paste or type the Room Code received from Player 1.");
        }
        ImGui::Unindent(180);

        ImGui::Dummy(ImVec2(0,14));
        ImGui::Separator();
        ImGui::Dummy(ImVec2(0,8));

        ImGui::AlignTextToFramePadding();
        ImGui::Text("Input Delay (Frames):");
        ImGui::SameLine(180);
        ImGui::SetNextItemWidth(160);
        ImGui::SliderInt("##join_delay",&p2p_delay,1,10,"%d frames");
        ImGui::SameLine();
        ImGui::TextColored(col(th.text_muted),"(Match host recommendation)");

        ImGui::AlignTextToFramePadding();
        ImGui::Text("Session ID:");
        ImGui::SameLine(180);
        ImGui::SetNextItemWidth(120);
        ImGui::InputInt("##join_session",&p2p_session_id,0,0);
        if(p2p_session_id<1)p2p_session_id=1;
        ImGui::SameLine();
        ImGui::TextColored(col(th.text_muted),"(Must match Host's Session ID)");

        ImGui::AlignTextToFramePadding();
        ImGui::Text("Local Bind Port:");
        ImGui::SameLine(180);
        ImGui::SetNextItemWidth(120);
        ImGui::InputInt("##join_port",&p2p_join_local_port,0,0);
        if(p2p_join_local_port<0)p2p_join_local_port=0;
        if(p2p_join_local_port>65535)p2p_join_local_port=65535;
        ImGui::SameLine();
        ImGui::TextColored(col(th.text_muted),"(0 = Automatic / OS assigned)");
    }

    ImGui::Dummy(ImVec2(0,16));
    if(p2p_status_msg[0]) {
        ImGui::TextColored(col(th.warn),"%s",p2p_status_msg);
    }

    ImGui::EndChild();

    ImGui::Dummy(ImVec2(0,4));
    const bool can_start=t3_compatible(m) && (p2p_mode==0 || (p2p_mode==1 && p2p_join_valid));
    ImGui::BeginDisabled(!can_start);
    ImGui::PushStyleColor(ImGuiCol_Button,col(th.accent));

    if(p2p_mode==0) {
        if(ImGui::Button("START HOST (WAIT FOR PLAYER 2)",ImVec2(320,40))) {
            m->s.netplay_launch={};
            m->s.netplay_launch.enabled=1;
            m->s.netplay_launch.local_slot=0;
            m->s.netplay_launch.input_player=-1;
            m->s.netplay_launch.session_id=(uint32_t)p2p_session_id;
            m->s.netplay_launch.input_delay=p2p_delay;
            m->s.netplay_launch.input_prediction=4;
            m->s.netplay_launch.player_count=2;
            m->s.netplay_launch.max_slots=2;
            m->s.netplay_launch.rollback=1;
            std::snprintf(m->s.netplay_launch.bind_hostport,sizeof(m->s.netplay_launch.bind_hostport),
                          "0.0.0.0:%d",p2p_host_port);
            m->s.netplay_launch.peer_hostport[0]='\0';
            if(mod_commit_netplay_launch(m)) {
                m->action=LNG_ACTION_LAUNCH;
            } else {
                std::snprintf(p2p_status_msg,sizeof(p2p_status_msg),"Failed to commit netplay configuration.");
            }
        }
    } else {
        if(ImGui::Button("CONNECT TO HOST & LAUNCH",ImVec2(320,40))) {
            m->s.netplay_launch={};
            m->s.netplay_launch.enabled=1;
            m->s.netplay_launch.local_slot=1;
            m->s.netplay_launch.input_player=-1;
            m->s.netplay_launch.session_id=(uint32_t)p2p_session_id;
            m->s.netplay_launch.input_delay=p2p_delay;
            m->s.netplay_launch.input_prediction=4;
            m->s.netplay_launch.player_count=2;
            m->s.netplay_launch.max_slots=2;
            m->s.netplay_launch.rollback=1;
            std::snprintf(m->s.netplay_launch.bind_hostport,sizeof(m->s.netplay_launch.bind_hostport),
                          "0.0.0.0:%d",p2p_join_local_port);
            std::snprintf(m->s.netplay_launch.peer_hostport,sizeof(m->s.netplay_launch.peer_hostport),
                          "%s",p2p_join_peer);
            if(mod_commit_netplay_launch(m)) {
                m->action=LNG_ACTION_LAUNCH;
            } else {
                std::snprintf(p2p_status_msg,sizeof(p2p_status_msg),"Failed to commit netplay configuration.");
            }
        }
    }
    ImGui::PopStyleColor();
    ImGui::EndDisabled();

    if(!can_start) {
        ImGui::SameLine();
        ImGui::AlignTextToFramePadding();
        if(!t3_compatible(m)) {
            ImGui::TextColored(col(th.warn),"Tekken 3 USA disc required to launch.");
        } else if(p2p_mode==1 && !p2p_join_valid) {
            ImGui::TextColored(col(th.warn),"Enter a valid Room Code above.");
        }
    }
}
static void tekken3_draw_launcher(LauncherModel* m,const LauncherTheme& th,int,int) {
    if(t3_observed_disc!=m->rom_full) {
        t3_observed_disc=m->rom_full;
        if(t3_discs.error.empty()) {
            t3_discs.attach(m->rom_full);t3_discs.selected=tekken3::DiscLibrary::normalize(m->rom_full);t3_discs.save();
        }
    }
    m->s.skip_launcher=0;
    m->s.aspect_index = t3_is_widescreen_mod_enabled(m) ? 1 : 0;
    m->s.widescreen = m->s.aspect_index;
    const auto* vp=ImGui::GetMainViewport();
    ImGui::SetNextWindowPos(vp->Pos);ImGui::SetNextWindowSize(vp->Size);
    ImGui::Begin("##TekkenLauncher",nullptr,ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoMove|
        ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoBringToFrontOnFocus);
    if(g_t3_logo.id && g_t3_logo.w>0) {
        const float logo_h = 58.f;
        const float logo_w = logo_h * ((float)g_t3_logo.w / (float)g_t3_logo.h);
        ImGui::SetCursorPosY(14);
        ImGui::Image(tid(g_t3_logo), ImVec2(logo_w, logo_h));
        ImGui::SameLine();
        ImGui::SetCursorPosY(38);
        ImGui::TextColored(col(th.accent), "FOR LINUX");
    } else {
        ImGui::PushFont(g_t3_title);ImGui::TextUnformatted("TEKKEN 3");ImGui::PopFont();
        ImGui::SameLine();ImGui::SetCursorPosY(43);
        ImGui::TextColored(col(th.accent), "FOR LINUX");
    }
    ImGui::SetCursorPosY(87);
    ImVec2 rule=ImGui::GetCursorScreenPos();
    ImGui::GetWindowDrawList()->AddRectFilled(rule,ImVec2(rule.x+ImGui::GetContentRegionAvail().x,rule.y+3),imcol(th.accent));
    ImGui::Dummy(ImVec2(0,17));
    const float body_h=std::max(200.f,ImGui::GetContentRegionAvail().y-77);
    const float nav_w=vp->Size.x<1050?164.f:202.f;
    ImGui::BeginChild("Menu",ImVec2(nav_w,body_h),ImGuiChildFlags_None);
    ImGui::TextColored(col(th.text_muted),"MAIN MENU");ImGui::Dummy(ImVec2(0,12));
    const char* names[]={"PLAY","MOD MANAGER","KEYBOARD","CONTROLLER","DISC LIBRARY","SETTINGS","MEMORY CARDS","ONLINE"};
    for(int page=0;page<8;page++) {
        if(page==T3_ONLINE && !m->netplay_supported)continue;
        const bool selected=(int)t3_page==page;
        if(selected)ImGui::PushStyleColor(ImGuiCol_Button,col(th.accent_dim));
        else ImGui::PushStyleColor(ImGuiCol_Button,col(th.background));
        ImGui::PushStyleVar(ImGuiStyleVar_ButtonTextAlign,ImVec2(.08f,.5f));
        if(ImGui::Button(names[page],ImVec2(-1,44)))t3_goto(m,(T3Page)page);
        ImGui::PopStyleVar();ImGui::PopStyleColor();
    }
    ImGui::Dummy(ImVec2(0,20));
    ImGui::TextColored(col(th.text_muted),"LOCAL SETUP");
    ImGui::TextWrapped("Shown before every game launch.");
    ImGui::EndChild();ImGui::SameLine(0,20);
    ImGui::BeginChild("Content",ImVec2(0,body_h),ImGuiChildFlags_Borders);
    switch(t3_page) {
        case T3_PLAY:t3_home(m,th);break;
        case T3_MODS:
            t3_heading("MOD MANAGER");
            ImGui::TextColored(col(th.text_muted),"Install packages, choose features and review compatibility.");
            ImGui::Spacing();if(m->mods)draw_mods(m,th);else ImGui::TextDisabled("Mod service unavailable in this build.");break;
        case T3_KEYBOARD:t3_keyboard(m,th);break;
        case T3_CONTROLLER:t3_heading("CONTROLLER MAPPING");t3_player_selector(m);draw_controller(m,th);break;
        case T3_DISCS:t3_library(m,th);break;
        case T3_SETTINGS:t3_settings(m,th);break;
        case T3_SAVES:t3_heading("MEMORY CARDS");panel_save_draw(m,&th);break;
        case T3_ONLINE:t3_p2p_netplay(m,th);break;
    }
    ImGui::EndChild();
    ImGui::Dummy(ImVec2(0,12));ImGui::Separator();ImGui::Dummy(ImVec2(0,5));
    ImGui::AlignTextToFramePadding();
    ImGui::TextColored(col(th.text_muted),"Setup applies on launch.  |  Esc cancels mapping.");
    ImGui::SameLine(ImGui::GetWindowContentRegionMax().x-330);
    if(ImGui::Button("EXIT",ImVec2(100,42)))m->action=LNG_ACTION_QUIT;
    ImGui::SameLine();
    const bool ready=(launcher_model_can_launch(m)||launcher_model_bios_blocks_play(m)) && t3_compatible(m);
    ImGui::BeginDisabled(!ready || m->capturing || m->hk_capturing);
    ImGui::PushStyleColor(ImGuiCol_Button,col(th.accent));
    if(ImGui::Button("LAUNCH GAME",ImVec2(210,42))) {
        if(launcher_model_bios_blocks_play(m))launcher_model_bios_play_prompt(m);
        else if(mod_commit_launch(m))m->action=LNG_ACTION_LAUNCH;
        else t3_goto(m,T3_MODS);
    }
    ImGui::PopStyleColor();ImGui::EndDisabled();
    draw_setup_wizard_modal(m,th);draw_bios_confirm_modal(m,th);draw_bios_play_modal(m,th);
    draw_pgo_confirm_modal(m,th);draw_fmv_timing_confirm_modal(m,th);
    draw_standalone_builtin_rom_picker(m,th);draw_restore_defaults_modal(m);
    ImGui::End();
}
