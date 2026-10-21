cmake_minimum_required(VERSION 3.20)
project(Tekken3Recomp LANGUAGES C CXX)

set(PSXRECOMP_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/psxrecomp" CACHE PATH
    "Path to psxrecomp")

# --- Opt-in product surfaces (OFF by default in the framework) -------------
# Scaffold prompts / flags fill these. Without recomp-ui, PSX_RECOMP_UI is OFF.
# Setup-host CI requires WIZARD_CMAKE_BLOCK / ENABLE_SETUP_WIZARD (FORCE_SETUP_HOST
# alone does not open first-run / Generate & rebuild).
# recomp-ui submodule present (PSX_RECOMP_UI defaults ON).
# Full netplay UI — enable after adding recomp-ui + testing:
# if(EXISTS "${PSXRECOMP_ROOT}/lib/recomp-net/CMakeLists.txt")
#     set(PSX_NETPLAY ON CACHE BOOL "…" FORCE)
# endif()
set(PSX_SETUP_WIZARD ON CACHE BOOL
    "Advertise first-run setup wizard + Generate & rebuild in recomp-ui" FORCE)
include("${PSXRECOMP_ROOT}/runtime/runtime.cmake")

option(TEKKEN3_BUILD_RECOMP_RUNTIME
    "Build the legacy hybrid recompilation/reference executable" ON)
if(TEKKEN3_BUILD_RECOMP_RUNTIME)
psxrecomp_add_game_runtime(psx-runtime
    # ENABLE_NETPLAY_IF_PRESENT
    # NETPLAY_LOBBY_URL "ws://netplay.retcomm.net:8765"
    ENABLE_SETUP_WIZARD
    WINDOW_TITLE "Tekken 3 Recompiled"
    DEFAULT_GAME_CONFIG_PATH "game.toml"
    MAX_PLAYERS 2
    # LAUNCHER_BOXART "${CMAKE_CURRENT_SOURCE_DIR}/launcher_assets/img/boxart.tga"
    GEN_MARKER "generated/SLUS_004.02_dispatch.c"
    GEN_FULL_GLOB "generated/SLUS_004.02_full_*.c"
    CODEGEN_SETUP_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/codegen_setup.c"
)

# Game-owned visual enhancements are trusted static plugins.  Package
# manifests can select them, but never load native code from an archive.
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/generated/SLUS_004.02_dispatch.c"
   AND NOT PSXRECOMP_FORCE_SETUP_HOST)
target_sources(psx-runtime PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_main_menu.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_new_skin_mods.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_widescreen_mod.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_fight_camera.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_forest_hd_mod.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_nina_skin_mod.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_xiaoyu_skin_mod.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_anna_skin_mod.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_anna_portrait_mod.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_kuma_skin_mod.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_unlock_characters_mod.c"
)

# Tekken's game-owned pre-launch frontend uses the native mod/input/disc services.
target_compile_definitions(psx-runtime PRIVATE TEKKEN3_LAUNCHER=1)
target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_80028CD4")
target_include_directories(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src")
add_custom_command(TARGET psx-runtime POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_CURRENT_SOURCE_DIR}/launcher_assets/fonts"
        "$<TARGET_FILE_DIR:psx-runtime>/assets/fonts"
    VERBATIM)

# Rebuild a narrow native camera variant from the current generated routine.
# Exact MIPS/operand guards keep this reproducible without editing guest RAM
# or maintaining a second hand-copied recompiler output file.
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(TEKKEN3_FIGHT_CAMERA_SOURCE "${CMAKE_CURRENT_BINARY_DIR}/tekken3_fight_camera_generated.c")
add_custom_target(tekken3_fight_camera_codegen
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/build_fight_camera.py"
        --source "${CMAKE_CURRENT_SOURCE_DIR}/generated/SLUS_004.02_full_26.c"
        --exe "${CMAKE_CURRENT_SOURCE_DIR}/disc/SLUS_004.02"
        --output "${TEKKEN3_FIGHT_CAMERA_SOURCE}"
    BYPRODUCTS "${TEKKEN3_FIGHT_CAMERA_SOURCE}"
    VERBATIM)
add_dependencies(psx-runtime tekken3_fight_camera_codegen)
target_sources(psx-runtime PRIVATE "${TEKKEN3_FIGHT_CAMERA_SOURCE}")
target_include_directories(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src")
set_source_files_properties("${TEKKEN3_FIGHT_CAMERA_SOURCE}" PROPERTIES
    INCLUDE_DIRECTORIES "${CMAKE_CURRENT_SOURCE_DIR}/generated")
target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_80064E10")
set_property(TARGET psx-runtime APPEND PROPERTY LINK_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded/packages/tekken3.gameplay.all-characters/1.0.0/manifest.toml"
    "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded/packages/tekken3.gameplay.all-characters/1.0.0/README.md"
    "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded/packages/tekken3.enhancement.true-widescreen/1.0.0/manifest.toml"
    "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded/packages/tekken3.enhancement.true-widescreen/1.0.0/README.md")

# A fresh installation enables Jun after the user imports the donor assets.
set(_tekken3_jun_default OFF)
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/workspace/jun-import/jun/Jun-TTT1-combat.jmv")
    set(_tekken3_jun_default ON)
endif()
option(TEKKEN3_JUN_EXPERIMENTAL "Build the Jun character import" ${_tekken3_jun_default})
if(TEKKEN3_JUN_EXPERIMENTAL)
    target_compile_definitions(psx-runtime PRIVATE TEKKEN3_JUN_EXPERIMENTAL=1)
    target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_jun_mod.c")
    set(JUN_GENERATED_DIR "${CMAKE_CURRENT_SOURCE_DIR}/workspace/jun-import/generated")
    if(NOT EXISTS "${JUN_GENERATED_DIR}/jun-render.exe_full_00.c")
        message(FATAL_ERROR "Prepare the local Jun assets with tools/prepare_jun_import.py first")
    endif()
    target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_jun_renderer.c")
    target_include_directories(psx-runtime PRIVATE "${JUN_GENERATED_DIR}")
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_80036CAC")
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_80035BC0")
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_80035190")
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_80035CE8")
    target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_jun_motion.c")
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_8003AD10")
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_80037CBC")
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_8006A3BC")
    target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_jun_combat.c")
    set(JUN_COMBAT_HOOKS "${CMAKE_CURRENT_BINARY_DIR}/tekken3_jun_combat_generated.c")
    set(JUN_PUSH_HOOKS "${CMAKE_CURRENT_BINARY_DIR}/tekken3_jun_push_generated.c")
    add_custom_target(tekken3_jun_combat_codegen
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/build_jun_combat_hooks.py"
            --root "${CMAKE_CURRENT_SOURCE_DIR}" --output "${JUN_COMBAT_HOOKS}"
        BYPRODUCTS "${JUN_COMBAT_HOOKS}" "${JUN_PUSH_HOOKS}" VERBATIM)
    add_dependencies(psx-runtime tekken3_jun_combat_codegen)
    target_sources(psx-runtime PRIVATE "${JUN_COMBAT_HOOKS}" "${JUN_PUSH_HOOKS}")
    set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/generated/SLUS_004.02_full_04.c" PROPERTIES HEADER_FILE_ONLY TRUE)
    set_source_files_properties("${JUN_COMBAT_HOOKS}" "${JUN_PUSH_HOOKS}" PROPERTIES
        INCLUDE_DIRECTORIES "${CMAKE_CURRENT_SOURCE_DIR}/generated")
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_8002F3AC" "-Wl,--wrap=func_8003F098" "-Wl,--wrap=func_8002DE24")
    target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_jun_voices.c")
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_80040C90"
        "-Wl,--wrap=spu_render" "-Wl,--wrap=spu_set_host_mix_volume"
        "-Wl,--wrap=spu_init" "-Wl,--wrap=spu_snapshot_read")
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_8002D178" "-Wl,--wrap=func_80038B4C" "-Wl,--wrap=func_800389C0")
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_8002D264" "-Wl,--wrap=func_8002E8D0")
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_8002E0BC")
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_8002CC28" "-Wl,--wrap=func_8002CD7C")
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_80059890")
    target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_jun_selector.c")
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=tekken3_outfits_input" "-Wl,--wrap=host_osd_outfit_image" "-Wl,--wrap=host_osd_draw_sdl")
    target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_jun_roster.c")
    target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_jun_stage.c")
    target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/tekken3_jun_stage_hooks.c")
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_800524EC" "-Wl,--wrap=func_80036600")
    target_link_options(psx-runtime PRIVATE
        "-Wl,--wrap=func_80052938" "-Wl,--wrap=func_80052940" "-Wl,--wrap=func_8004B790" "-Wl,--wrap=func_8004B928"
        "-Wl,--wrap=func_80031BFC" "-Wl,--wrap=func_80052AD0"
        "-Wl,--wrap=func_80052958" "-Wl,--wrap=func_80052990" "-Wl,--wrap=func_8006BF20"
        "-Wl,--wrap=func_8003626C" "-Wl,--wrap=func_80036294" "-Wl,--wrap=func_800362C4"
        "-Wl,--wrap=func_8003F044"
        "-Wl,--wrap=func_800513C0" "-Wl,--wrap=func_80051464" "-Wl,--wrap=func_8005155C" "-Wl,--wrap=func_80051660"
        "-Wl,--wrap=func_80052948")
endif()
if(NOT TEKKEN3_JUN_EXPERIMENTAL)
    target_link_options(psx-runtime PRIVATE "-Wl,--wrap=func_80031BFC")
endif()

# A dynamic developer build can import the bundled Clang C++ runtime.  Stage it
# when that actually happens; production builds use PSX_STATIC_RUNTIME and need
# no non-system DLLs beside the executable.
if(WIN32 AND NOT PSX_STATIC_RUNTIME)
    get_filename_component(_tekken3_compiler_bin "${CMAKE_CXX_COMPILER}" DIRECTORY)
    foreach(_tekken3_runtime_dll IN ITEMS libc++.dll libunwind.dll)
        if(EXISTS "${_tekken3_compiler_bin}/${_tekken3_runtime_dll}")
            add_custom_command(TARGET psx-runtime POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    "${_tekken3_compiler_bin}/${_tekken3_runtime_dll}"
                    "$<TARGET_FILE_DIR:psx-runtime>/${_tekken3_runtime_dll}"
                VERBATIM
            )
        endif()
    endforeach()
elseif(WIN32)
    add_custom_command(TARGET psx-runtime POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E rm -f
            "$<TARGET_FILE_DIR:psx-runtime>/libc++.dll"
            "$<TARGET_FILE_DIR:psx-runtime>/libunwind.dll"
        VERBATIM
    )
endif()

# Stage the reviewed Tekken-specific catalog after the framework catalog.  The
# framework's own POST_BUILD step recreates mods/, so ordering this command
# here preserves both catalogs and also removes stale game packages.
add_custom_command(TARGET psx-runtime POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E rm -rf
        "$<TARGET_FILE_DIR:psx-runtime>/mods/packages/tekken3.enhancement.true-widescreen"
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded/packages"
        "$<TARGET_FILE_DIR:psx-runtime>/mods/packages"
    COMMENT "Staging Tekken 3 built-in mod catalog"
    VERBATIM
)
add_custom_command(TARGET psx-runtime POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/forest-hd"
        "$<TARGET_FILE_DIR:psx-runtime>/mods/forest-hd"
    COMMENT "Staging forest HD texture assets"
    VERBATIM
)
add_custom_command(TARGET psx-runtime POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/nina-white-satin"
        "$<TARGET_FILE_DIR:psx-runtime>/mods/nina-white-satin"
    COMMENT "Staging Nina White Satin textures"
    VERBATIM
)
add_custom_command(TARGET psx-runtime POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/xiaoyu-cherry-blossom"
        "$<TARGET_FILE_DIR:psx-runtime>/mods/xiaoyu-cherry-blossom"
    COMMENT "Staging Xiaoyu Cherry Blossom Ribbon textures"
    VERBATIM
)
add_custom_command(TARGET psx-runtime POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/anna-jessica-rabbit"
        "$<TARGET_FILE_DIR:psx-runtime>/mods/anna-jessica-rabbit"
    COMMENT "Staging Anna Jessica Rabbit textures"
    VERBATIM
)
set_property(TARGET psx-runtime APPEND PROPERTY LINK_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/anna-portrait/portrait.tim"
    "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded/packages/tekken3.art.anna-portrait/1.0.0/manifest.toml")
add_custom_command(TARGET psx-runtime POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/anna-portrait"
        "$<TARGET_FILE_DIR:psx-runtime>/mods/anna-portrait"
    COMMENT "Staging Anna portrait artwork"
    VERBATIM
)
file(GLOB TEKKEN3_GALLERY_ASSETS CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/outfit-menu/*")
foreach(_new_skin IN ITEMS eddy-monochrome julia-blue heihachi-tiger-coat)
    file(GLOB _new_skin_assets CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/${_new_skin}/*")
    set_property(TARGET psx-runtime APPEND PROPERTY LINK_DEPENDS ${_new_skin_assets}
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded/packages/tekken3.skin.${_new_skin}/1.0.0/manifest.toml")
    add_custom_command(TARGET psx-runtime POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_directory
            "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/${_new_skin}"
            "$<TARGET_FILE_DIR:psx-runtime>/mods/${_new_skin}"
        VERBATIM)
endforeach()
file(GLOB TEKKEN3_KUMA_ASSETS CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/kuma-polar-bear/*")
set_property(TARGET psx-runtime APPEND PROPERTY LINK_DEPENDS ${TEKKEN3_KUMA_ASSETS}
    "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded/packages/tekken3.skin.kuma-polar-bear/1.0.0/manifest.toml")
add_custom_command(TARGET psx-runtime POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/kuma-polar-bear"
        "$<TARGET_FILE_DIR:psx-runtime>/mods/kuma-polar-bear"
    COMMENT "Staging Kuma Polar Bear textures"
    VERBATIM)
set_property(TARGET psx-runtime APPEND PROPERTY LINK_DEPENDS ${TEKKEN3_GALLERY_ASSETS})
add_custom_command(TARGET psx-runtime POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/outfit-menu"
        "$<TARGET_FILE_DIR:psx-runtime>/mods/outfit-menu"
    COMMENT "Staging skin gallery artwork and catalog"
    VERBATIM
)

# Local imports also work in the normal recomp launch. Keep the original ROM
# dumps and generated packs private; stage only the runtime artifacts.
if(TEKKEN3_JUN_EXPERIMENTAL)
    set(JUN_RUNTIME_FILES
        Jun-TTT1-arcade-P1.3dm Jun-TTT1-arcade-P1.relocs Jun-TTT1-arcade-P1.tim
        Jun-TTT1-arcade-P2.3dm Jun-TTT1-arcade-P2.relocs Jun-TTT1-arcade-P2.tim
        Jun-TTT1-arcade-P3.3dm Jun-TTT1-arcade-P3.relocs Jun-TTT1-arcade-P3.tim
        Jun-TTT1-idle.poses Jun-TTT1-combat.jmv Jun-TTT1-tables.jst Jun-TTT1-voices.juv
        Jun-T3-ui.jui Jun-T3-name.4bpp)
    set(JUN_RUNTIME_ASSETS)
    foreach(JUN_FILE IN LISTS JUN_RUNTIME_FILES)
        list(APPEND JUN_RUNTIME_ASSETS "${CMAKE_CURRENT_SOURCE_DIR}/workspace/jun-import/jun/${JUN_FILE}")
    endforeach()
    set(JUN_PACKAGE "${CMAKE_CURRENT_SOURCE_DIR}/mods/local-packages/tekken3.character.jun-probe/1.0.0/manifest.toml")
    set_property(TARGET psx-runtime APPEND PROPERTY LINK_DEPENDS ${JUN_RUNTIME_ASSETS} "${JUN_PACKAGE}")
    add_custom_command(TARGET psx-runtime POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_directory
            "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/jun-heavenly-garden/native"
            "$<TARGET_FILE_DIR:psx-runtime>/mods/jun-heavenly-garden"
        COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:psx-runtime>/mods/jun"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different ${JUN_RUNTIME_ASSETS} "$<TARGET_FILE_DIR:psx-runtime>/mods/jun"
        COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:psx-runtime>/mods/packages/tekken3.character.jun-probe/1.0.0"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different "${JUN_PACKAGE}" "$<TARGET_FILE_DIR:psx-runtime>/mods/packages/tekken3.character.jun-probe/1.0.0/manifest.toml"
        COMMENT "Staging private Jun character for the normal recomp launch"
        VERBATIM)
    set_property(TARGET psx-runtime APPEND PROPERTY LINK_DEPENDS
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/jun-heavenly-garden/native/Heavenly-Garden.arc"
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/jun-heavenly-garden/native/Heavenly-Garden.mesh"
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/jun-heavenly-garden/native/background.rgba"
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/jun-heavenly-garden/native/ground.rgba"
        "${CMAKE_CURRENT_SOURCE_DIR}/mods/assets/jun-heavenly-garden/native/background-mapping.bin")
endif()

endif()

endif() # Full game enhancements need locally generated game code.

# The recompiled executable above remains a behavioral oracle while the game is
# migrated system-by-system.  The PC-port target below is deliberately separate:
# it does not compile generated guest code, OpenBIOS, the PS1 GPU/GTE, or the
# compatibility scheduler.
option(TEKKEN3_BUILD_PC_PORT "Build the independent native Tekken 3 PC port" OFF)
if(TEKKEN3_BUILD_PC_PORT)
    add_subdirectory(native)
endif()
