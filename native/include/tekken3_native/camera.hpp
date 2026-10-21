#pragma once

#include "tekken3_native/math.hpp"

namespace tekken3::native {

struct CameraFrame {
    Vec3 eye{};
    Vec3 target{};
    float aspect = 16.0f / 9.0f;
    float vertical_fov = 48.0f * kPi / 180.0f;
    float horizontal_fov = 0.0f;
    Mat4 view = Mat4::identity();
    Mat4 projection = Mat4::identity();
};

class CameraRig {
public:
    void reset(float center_x = 0.0f);
    void update(float player_one_x, float player_two_x, float dt);
    CameraFrame frame(int pixel_width, int pixel_height) const;

    float center_x() const { return center_x_; }

private:
    float center_x_ = 0.0f;
    float fighter_span_ = 5.0f;
};

}  // namespace tekken3::native
