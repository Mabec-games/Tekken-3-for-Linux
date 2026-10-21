#pragma once

#include <algorithm>
#include <cmath>

namespace tekken3::native {

constexpr float kPi = 3.14159265358979323846f;

struct Vec3 {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
};

inline Vec3 operator+(Vec3 a, Vec3 b) { return {a.x + b.x, a.y + b.y, a.z + b.z}; }
inline Vec3 operator-(Vec3 a, Vec3 b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
inline Vec3 operator*(Vec3 value, float scale) { return {value.x * scale, value.y * scale, value.z * scale}; }
inline float dot(Vec3 a, Vec3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
inline Vec3 cross(Vec3 a, Vec3 b) {
    return {a.y * b.z - a.z * b.y,
            a.z * b.x - a.x * b.z,
            a.x * b.y - a.y * b.x};
}
inline Vec3 normalize(Vec3 value) {
    const float length = std::sqrt(std::max(dot(value, value), 0.000001f));
    return value * (1.0f / length);
}

struct Mat4 {
    float v[16]{};

    static Mat4 identity() {
        Mat4 result{};
        result.v[0] = result.v[5] = result.v[10] = result.v[15] = 1.0f;
        return result;
    }
};

inline Mat4 operator*(const Mat4& a, const Mat4& b) {
    Mat4 result{};
    for (int column = 0; column < 4; ++column) {
        for (int row = 0; row < 4; ++row) {
            for (int k = 0; k < 4; ++k) {
                result.v[column * 4 + row] +=
                    a.v[k * 4 + row] * b.v[column * 4 + k];
            }
        }
    }
    return result;
}

inline Mat4 translation(Vec3 value) {
    Mat4 result = Mat4::identity();
    result.v[12] = value.x;
    result.v[13] = value.y;
    result.v[14] = value.z;
    return result;
}

inline Mat4 scale(Vec3 value) {
    Mat4 result{};
    result.v[0] = value.x;
    result.v[5] = value.y;
    result.v[10] = value.z;
    result.v[15] = 1.0f;
    return result;
}

inline Mat4 rotation_y(float radians) {
    Mat4 result = Mat4::identity();
    const float cosine = std::cos(radians);
    const float sine = std::sin(radians);
    result.v[0] = cosine;
    result.v[2] = -sine;
    result.v[8] = sine;
    result.v[10] = cosine;
    return result;
}

inline Mat4 perspective(float vertical_fov_radians, float aspect,
                        float near_plane, float far_plane) {
    const float focal = 1.0f / std::tan(vertical_fov_radians * 0.5f);
    Mat4 result{};
    result.v[0] = focal / std::max(aspect, 0.01f);
    result.v[5] = focal;
    result.v[10] = (far_plane + near_plane) / (near_plane - far_plane);
    result.v[11] = -1.0f;
    result.v[14] = (2.0f * far_plane * near_plane) / (near_plane - far_plane);
    return result;
}

inline Mat4 orthographic(float left, float right, float bottom, float top,
                         float near_plane, float far_plane) {
    Mat4 result = Mat4::identity();
    result.v[0] = 2.0f / (right - left);
    result.v[5] = 2.0f / (top - bottom);
    result.v[10] = -2.0f / (far_plane - near_plane);
    result.v[12] = -(right + left) / (right - left);
    result.v[13] = -(top + bottom) / (top - bottom);
    result.v[14] = -(far_plane + near_plane) / (far_plane - near_plane);
    return result;
}

inline Mat4 look_at(Vec3 eye, Vec3 target, Vec3 up) {
    const Vec3 forward = normalize(target - eye);
    const Vec3 side = normalize(cross(forward, up));
    const Vec3 corrected_up = cross(side, forward);

    Mat4 result = Mat4::identity();
    result.v[0] = side.x;
    result.v[1] = corrected_up.x;
    result.v[2] = -forward.x;
    result.v[4] = side.y;
    result.v[5] = corrected_up.y;
    result.v[6] = -forward.y;
    result.v[8] = side.z;
    result.v[9] = corrected_up.z;
    result.v[10] = -forward.z;
    result.v[12] = -dot(side, eye);
    result.v[13] = -dot(corrected_up, eye);
    result.v[14] = dot(forward, eye);
    return result;
}

}  // namespace tekken3::native
