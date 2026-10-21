#pragma once

#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

namespace tekken3::native {

struct DiscTrack {
    int number = 0;
    bool is_audio = false;
    std::uint32_t start_lba = 0;
    std::uint32_t pregap_lba = 0;
};

// Result of inspecting a player-supplied disc image. The native port reads
// assets from that image in place; inspection never extracts or caches them.
struct DiscReport {
    bool ok = false;
    std::string detail;

    // Canonical mount selected by the shared resolver. This can be a CUE even
    // when the player selected one of its BIN tracks.
    std::filesystem::path mount_path;
    std::string volume_id;
    int track_count = 0;
    std::vector<DiscTrack> tracks;

    // Observed identity fields are retained for useful mismatch diagnostics.
    std::string boot_path;
    std::uintmax_t boot_executable_size = 0;
    std::uint32_t load_address = 0;
    std::uint32_t entry_pc = 0;
    std::uint32_t text_size = 0;
};

DiscReport inspect_disc(const std::filesystem::path& path);

}  // namespace tekken3::native
