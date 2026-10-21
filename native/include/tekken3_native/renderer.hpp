#pragma once

#include "tekken3_native/game.hpp"

#include <filesystem>
#include <string>

namespace tekken3::native {

// OpenGL 3.1 renderer for the independent native-PC-port prototype. The caller
// owns the window and GL context; initialize(), render(), capture_png(), and
// shutdown() must all run while that context is current on the calling thread.
class RendererGL final {
public:
    RendererGL() = default;
    ~RendererGL() = default;

    RendererGL(const RendererGL&) = delete;
    RendererGL& operator=(const RendererGL&) = delete;

    bool initialize();
    void shutdown();

    bool render(const MatchState& match, int pixel_width, int pixel_height);

    bool capture_png(const std::string& path, int pixel_width, int pixel_height);
    bool capture_png(const char* path, int pixel_width, int pixel_height);
    bool capture_png(const std::filesystem::path& path,
                     int pixel_width, int pixel_height);

    bool initialized() const noexcept { return initialized_; }
    const std::string& error() const noexcept { return error_; }

private:
    void draw_box(const Mat4& view_projection, const Mat4& model,
                  float red, float green, float blue, float alpha,
                  bool lit);
    void draw_stage(const CameraFrame& camera);
    void draw_fighter(const CameraFrame& camera, const FighterState& fighter,
                      int fighter_index);
    void draw_hud(const MatchState& match, int pixel_width, int pixel_height);
    void draw_hud_rect(const Mat4& projection, float x, float y,
                       float width, float height,
                       float red, float green, float blue, float alpha = 1.0f);
    void draw_digit(const Mat4& projection, int digit, float x, float y,
                    float width, float height, float thickness,
                    float red, float green, float blue);
    void set_error(std::string message);

    unsigned int program_ = 0;
    unsigned int vertex_array_ = 0;
    unsigned int vertex_buffer_ = 0;
    unsigned int index_buffer_ = 0;
    int index_count_ = 0;

    int position_attribute_ = -1;
    int normal_attribute_ = -1;
    int mvp_uniform_ = -1;
    int model_uniform_ = -1;
    int color_uniform_ = -1;
    int lit_uniform_ = -1;

    bool initialized_ = false;
    std::string error_{};
};

// Keep the main-loop spelling concise while retaining an explicit backend name.
using Renderer = RendererGL;

}  // namespace tekken3::native
