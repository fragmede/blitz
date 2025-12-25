// THE SHADER - All rendering in one fragment shader
// Renders: background, player, enemies, bullets, explosions, UI

#version 330 core

out vec4 fragColor;

// Uniforms
uniform vec2 u_resolution;
uniform float u_time;
uniform vec2 u_player_pos;
uniform int u_score;
uniform int u_lives;
uniform int u_entity_count;

// Entity data texture (512 entities, RGBA32F)
// Each texel: (x, y, type_flags, data)
// type_flags: integer part = type (1=player, 2=bullet, 3=enemy, 4=explosion)
uniform sampler2D u_entities;

// Constants
const float PI = 3.14159265359;
const int ENTITY_PLAYER = 1;
const int ENTITY_BULLET = 2;
const int ENTITY_ENEMY = 3;
const int ENTITY_EXPLOSION = 4;

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);

    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));

    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

// =============================================================================
// SDF PRIMITIVES
// =============================================================================

float sdCircle(vec2 p, float r) {
    return length(p) - r;
}

float sdBox(vec2 p, vec2 b) {
    vec2 d = abs(p) - b;
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);
}

float sdTriangle(vec2 p, float r) {
    const float k = sqrt(3.0);
    p.x = abs(p.x) - r;
    p.y = p.y + r / k;
    if (p.x + k * p.y > 0.0) p = vec2(p.x - k * p.y, -k * p.x - p.y) / 2.0;
    p.x -= clamp(p.x, -2.0 * r, 0.0);
    return -length(p) * sign(p.y);
}

float sdStar(vec2 p, float r, int n, float m) {
    float an = PI / float(n);
    float en = PI / m;
    vec2 acs = vec2(cos(an), sin(an));
    vec2 ecs = vec2(cos(en), sin(en));

    float bn = mod(atan(p.x, p.y), 2.0 * an) - an;
    p = length(p) * vec2(cos(bn), abs(sin(bn)));

    p -= r * acs;
    p += ecs * clamp(-dot(p, ecs), 0.0, r * acs.y / ecs.y);
    return length(p) * sign(p.x);
}

// =============================================================================
// ENTITY RENDERING
// =============================================================================

vec4 renderPlayer(vec2 uv, vec2 pos) {
    vec2 p = uv - pos;

    // Ship body (triangle pointing up)
    float ship = sdTriangle(p * vec2(1.0, -1.0), 18.0);

    // Wings
    float wing1 = sdBox(p - vec2(-15.0, 5.0), vec2(8.0, 3.0));
    float wing2 = sdBox(p - vec2(15.0, 5.0), vec2(8.0, 3.0));
    ship = min(ship, min(wing1, wing2));

    // Engine glow
    float engine = sdCircle(p - vec2(0.0, 15.0), 6.0 + sin(u_time * 20.0) * 2.0);

    vec4 color = vec4(0.0);

    // Ship color (cyan/blue gradient)
    if (ship < 0.0) {
        float t = clamp(-ship / 18.0, 0.0, 1.0);
        color = vec4(0.2, 0.8, 1.0, 1.0) * (0.7 + 0.3 * t);
    }

    // Ship outline glow
    float glow = exp(-ship * 0.15) * 0.5;
    color.rgb += vec3(0.3, 0.7, 1.0) * glow;

    // Engine flame
    if (engine < 0.0) {
        color = vec4(1.0, 0.6, 0.2, 1.0);
    }
    float engineGlow = exp(-engine * 0.1) * 0.8;
    color.rgb += vec3(1.0, 0.4, 0.1) * engineGlow;

    return color;
}

vec4 renderBullet(vec2 uv, vec2 pos) {
    vec2 p = uv - pos;

    float bullet = sdBox(p, vec2(3.0, 8.0));

    vec4 color = vec4(0.0);

    if (bullet < 0.0) {
        color = vec4(1.0, 1.0, 0.3, 1.0);
    }

    // Glow
    float glow = exp(-bullet * 0.2) * 0.6;
    color.rgb += vec3(1.0, 0.8, 0.2) * glow;

    return color;
}

vec4 renderEnemy(vec2 uv, vec2 pos, float data) {
    vec2 p = uv - pos;

    // Rotate slightly based on time
    float angle = sin(u_time * 2.0 + pos.x * 0.1) * 0.2;
    float c = cos(angle), s = sin(angle);
    p = mat2(c, -s, s, c) * p;

    // Enemy shape (inverted triangle with details)
    float body = sdTriangle(p, 15.0);

    // Eyes
    float eye1 = sdCircle(p - vec2(-6.0, -3.0), 4.0);
    float eye2 = sdCircle(p - vec2(6.0, -3.0), 4.0);

    vec4 color = vec4(0.0);

    // Body (red/orange)
    if (body < 0.0) {
        color = vec4(1.0, 0.3, 0.2, 1.0);
    }

    // Eyes (yellow)
    if (eye1 < 0.0 || eye2 < 0.0) {
        color = vec4(1.0, 1.0, 0.0, 1.0);
    }

    // Glow
    float glow = exp(-body * 0.12) * 0.4;
    color.rgb += vec3(1.0, 0.2, 0.1) * glow;

    return color;
}

vec4 renderExplosion(vec2 uv, vec2 pos, float lifetime) {
    vec2 p = uv - pos;

    float t = lifetime * 2.0;  // 0 to 1 over 0.5 seconds

    // Expanding ring
    float radius = t * 40.0;
    float ring = abs(length(p) - radius) - 3.0 * (1.0 - t);

    // Particles
    float particles = 1e10;
    for (int i = 0; i < 8; i++) {
        float angle = float(i) * PI * 0.25;
        vec2 dir = vec2(cos(angle), sin(angle));
        vec2 particlePos = dir * t * 30.0;
        float particle = sdCircle(p - particlePos, 4.0 * (1.0 - t));
        particles = min(particles, particle);
    }

    vec4 color = vec4(0.0);

    // Ring
    if (ring < 0.0) {
        float fade = 1.0 - t;
        color = vec4(1.0, 0.6, 0.2, fade);
    }

    // Particles
    if (particles < 0.0) {
        float fade = 1.0 - t;
        color = max(color, vec4(1.0, 0.8, 0.3, fade));
    }

    // Central flash (early)
    if (t < 0.3) {
        float flash = sdCircle(p, 20.0 * (0.3 - t) / 0.3);
        if (flash < 0.0) {
            color = vec4(1.0, 1.0, 0.8, 1.0);
        }
    }

    // Glow
    float glow = exp(-min(ring, particles) * 0.1) * (1.0 - t) * 0.5;
    color.rgb += vec3(1.0, 0.5, 0.1) * glow;

    return color;
}

// =============================================================================
// BACKGROUND
// =============================================================================

vec4 renderBackground(vec2 uv) {
    vec3 color = vec3(0.02, 0.02, 0.08);  // Deep space blue

    // Scrolling starfield (multiple layers for parallax)
    for (int layer = 0; layer < 3; layer++) {
        float speed = 20.0 + float(layer) * 30.0;
        float size = 1.0 + float(layer) * 0.5;
        float brightness = 0.3 + float(layer) * 0.2;

        vec2 starUV = uv;
        starUV.y = mod(starUV.y + u_time * speed, u_resolution.y);

        // Grid of potential star positions
        vec2 gridSize = vec2(40.0 - float(layer) * 10.0);
        vec2 cell = floor(starUV / gridSize);
        vec2 cellUV = mod(starUV, gridSize) - gridSize * 0.5;

        // Random star position within cell
        float starHash = hash(cell + float(layer) * 100.0);
        if (starHash > 0.7) {
            vec2 starOffset = (vec2(hash(cell * 2.0), hash(cell * 3.0)) - 0.5) * gridSize * 0.8;
            float d = length(cellUV - starOffset);

            // Star with twinkle
            float twinkle = 0.5 + 0.5 * sin(u_time * 3.0 + starHash * 10.0);
            float star = smoothstep(size, 0.0, d) * brightness * twinkle;

            color += star * vec3(0.8, 0.9, 1.0);
        }
    }

    // Subtle nebula
    float nebula = noise(uv * 0.005 + u_time * 0.01);
    nebula = pow(nebula, 3.0) * 0.15;
    color += nebula * vec3(0.3, 0.1, 0.4);

    return vec4(color, 1.0);
}

// =============================================================================
// UI RENDERING
// =============================================================================

// 7-segment digit rendering
float renderDigit(vec2 p, int digit) {
    // Segments: top, top-right, bottom-right, bottom, bottom-left, top-left, middle
    bool segments[10 * 7] = bool[](
        // 0
        true, true, true, true, true, true, false,
        // 1
        false, true, true, false, false, false, false,
        // 2
        true, true, false, true, true, false, true,
        // 3
        true, true, true, true, false, false, true,
        // 4
        false, true, true, false, false, true, true,
        // 5
        true, false, true, true, false, true, true,
        // 6
        true, false, true, true, true, true, true,
        // 7
        true, true, true, false, false, false, false,
        // 8
        true, true, true, true, true, true, true,
        // 9
        true, true, true, true, false, true, true
    );

    float w = 2.0;  // Segment width
    float h = 6.0;  // Segment length

    float d = 1e10;

    int base = digit * 7;

    // Top
    if (segments[base + 0])
        d = min(d, sdBox(p - vec2(0.0, h + w), vec2(h, w)));
    // Top-right
    if (segments[base + 1])
        d = min(d, sdBox(p - vec2(h, h * 0.5 + w), vec2(w, h * 0.5)));
    // Bottom-right
    if (segments[base + 2])
        d = min(d, sdBox(p - vec2(h, -h * 0.5 - w), vec2(w, h * 0.5)));
    // Bottom
    if (segments[base + 3])
        d = min(d, sdBox(p - vec2(0.0, -h - w), vec2(h, w)));
    // Bottom-left
    if (segments[base + 4])
        d = min(d, sdBox(p - vec2(-h, -h * 0.5 - w), vec2(w, h * 0.5)));
    // Top-left
    if (segments[base + 5])
        d = min(d, sdBox(p - vec2(-h, h * 0.5 + w), vec2(w, h * 0.5)));
    // Middle
    if (segments[base + 6])
        d = min(d, sdBox(p, vec2(h, w)));

    return d;
}

vec4 renderScore(vec2 uv, int score) {
    vec4 color = vec4(0.0);

    vec2 scorePos = vec2(70.0, u_resolution.y - 30.0);
    vec2 p = uv - scorePos;

    // Render up to 6 digits
    int s = score;
    for (int i = 5; i >= 0; i--) {
        int digit = s % 10;
        s /= 10;

        vec2 digitPos = p - vec2(float(i) * 20.0 - 50.0, 0.0);
        float d = renderDigit(digitPos, digit);

        if (d < 0.0) {
            color = vec4(0.2, 1.0, 0.3, 1.0);
        }

        float glow = exp(-d * 0.15) * 0.3;
        color.rgb += vec3(0.2, 1.0, 0.3) * glow;
    }

    return color;
}

vec4 renderLives(vec2 uv, int lives) {
    vec4 color = vec4(0.0);

    vec2 livesPos = vec2(u_resolution.x - 100.0, u_resolution.y - 30.0);

    for (int i = 0; i < lives && i < 5; i++) {
        vec2 p = uv - livesPos - vec2(float(i) * 25.0, 0.0);

        // Mini ship icon
        float ship = sdTriangle(p * vec2(1.0, -1.0), 8.0);

        if (ship < 0.0) {
            color = vec4(0.3, 0.8, 1.0, 1.0);
        }

        float glow = exp(-ship * 0.2) * 0.3;
        color.rgb += vec3(0.3, 0.8, 1.0) * glow;
    }

    return color;
}

// =============================================================================
// MAIN
// =============================================================================

void main() {
    vec2 uv = gl_FragCoord.xy;

    // Start with background
    vec4 color = renderBackground(uv);

    // Render entities from texture
    for (int i = 0; i < 512; i++) {
        if (i >= u_entity_count * 2) break;  // Early out

        vec4 entityData = texelFetch(u_entities, ivec2(i, 0), 0);
        float x = entityData.x;
        float y = entityData.y;
        int entityType = int(entityData.z);
        float data = entityData.w;

        if (entityType == 0) continue;  // Inactive

        vec2 pos = vec2(x, y);

        // Only render if reasonably close to this pixel (optimization)
        float dist = length(uv - pos);
        if (dist > 100.0) continue;

        vec4 entityColor = vec4(0.0);

        if (entityType == ENTITY_PLAYER) {
            entityColor = renderPlayer(uv, pos);
        } else if (entityType == ENTITY_BULLET) {
            entityColor = renderBullet(uv, pos);
        } else if (entityType == ENTITY_ENEMY) {
            entityColor = renderEnemy(uv, pos, data);
        } else if (entityType == ENTITY_EXPLOSION) {
            entityColor = renderExplosion(uv, pos, data);
        }

        // Blend entity over background
        color.rgb = mix(color.rgb, entityColor.rgb, entityColor.a);
        color.a = max(color.a, entityColor.a);
    }

    // Render UI on top
    vec4 scoreColor = renderScore(uv, u_score);
    color.rgb = mix(color.rgb, scoreColor.rgb, scoreColor.a);

    vec4 livesColor = renderLives(uv, u_lives);
    color.rgb = mix(color.rgb, livesColor.rgb, livesColor.a);

    fragColor = color;
}
