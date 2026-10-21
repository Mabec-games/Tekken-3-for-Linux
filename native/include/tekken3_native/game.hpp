#pragma once

#include "tekken3_native/camera.hpp"

namespace tekken3::native {

enum class AttackKind {
    none,
    light,
    heavy,
};

struct InputFrame {
    float move_axis = 0.0f;
    bool jump = false;
    bool light_attack = false;
    bool heavy_attack = false;
    bool restart = false;
};

struct FighterState {
    float x = 0.0f;
    float y = 0.0f;
    float vertical_velocity = 0.0f;
    float health = 100.0f;
    float attack_age = 0.0f;
    float attack_duration = 0.0f;
    float hit_flash = 0.0f;
    int facing = 1;
    AttackKind attack = AttackKind::none;
    bool attack_connected = false;
};

struct MatchState {
    FighterState fighters[2]{};
    CameraRig camera{};
    float round_time = 60.0f;
    float end_delay = 0.0f;
    unsigned round_number = 1;
    bool round_over = false;
};

class NativeGame {
public:
    explicit NativeGame(bool enable_cpu_opponent = true);

    void reset_round();
    void step(float dt, const InputFrame& input);

    const MatchState& state() const { return state_; }

private:
    void begin_attack(FighterState& fighter, AttackKind kind);
    void update_fighter(FighterState& fighter, float dt, float move_axis, bool jump);
    void resolve_attack(FighterState& attacker, FighterState& defender);

    MatchState state_{};
    bool cpu_opponent_ = true;
    bool previous_jump_ = false;
};

}  // namespace tekken3::native
