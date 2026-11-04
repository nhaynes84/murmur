// MURMUR — scales and note names. The plant chooses WHEN and HOW FAR; the scale keeps it musical.
#pragma once
#include <Arduino.h>

namespace music {
struct Scale {
  const char* mood;   // what she sees: how it FEELS, not music theory
  const char* name;
  uint8_t n;
  uint8_t steps[12];
};

static const Scale SCALES[] = {
    {"Dreamy", "Pentatonic", 5, {0, 2, 4, 7, 9}},
    {"Mellow", "Minor Pent.", 5, {0, 3, 5, 7, 10}},
    {"Bright", "Major", 7, {0, 2, 4, 5, 7, 9, 11}},
    {"Moody", "Minor", 7, {0, 2, 3, 5, 7, 8, 10}},
    {"Wistful", "Dorian", 7, {0, 2, 3, 5, 7, 9, 10}},
    {"Zen", "In-Sen", 5, {0, 1, 5, 7, 10}},
    {"Floaty", "Whole Tone", 6, {0, 2, 4, 6, 8, 10}},
    {"Wild", "Chromatic", 12, {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}},
    {"Raga", "Bhairav", 7, {0, 1, 4, 5, 7, 8, 11}},   // best with the bass drone (the tanpura)
};
static const uint8_t N_SCALES = sizeof(SCALES) / sizeof(SCALES[0]);
static const char* KEYS[12] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};

// degree (can be negative) in a scale -> MIDI note, rooted on `root` (0..11) around `base_octave`
inline uint8_t note(const Scale& s, int degree, int root, int base_octave = 4) {
  int oct = degree >= 0 ? degree / s.n : -((-degree + s.n - 1) / s.n);
  int idx = degree - oct * s.n;
  int n = 12 * (base_octave + 1 + oct) + root + s.steps[idx];
  return (uint8_t)constrain(n, 24, 108);
}

// ★ a "sister" mood for big events: the plant can tip the feeling for a while, then it comes home.
//   Dreamy<->Mellow, Bright<->Moody, Wistful->Moody, Zen->Mellow, Floaty->Dreamy, Wild->Wistful, Raga->Wistful (Kafi)
static const uint8_t SISTER[] = {1, 0, 3, 2, 3, 1, 0, 4, 4};

// a root offset of k fifths from home, folded to -5..+6 semitones so the register doesn't jump
inline int fifths(int k) { int s = ((k * 7) % 12 + 12) % 12; return s > 6 ? s - 12 : s; }

inline String name(uint8_t midi) { return String(KEYS[midi % 12]) + String(midi / 12 - 1); }
}  // namespace music
