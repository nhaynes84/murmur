// MURMUR — the plant plays; the box listens.
//
// A TLC555 oscillates with the PLANT as its timing resistor; its pulses arrive on IO17. Every
// pulse's period is a reading of the plant. We look at windows of 10 pulses: when a window's mean
// moves further than the plant's own recent noise x the sensitivity, that is an EVENT -> a note.
//   pitch    = where the reading sits relative to its slow baseline, snapped to the chosen scale
//   velocity = how big the jump was
//   length   = how slowly the plant is talking (slow plant, long notes)
//   CC74     = the slow drift itself, continuously (filter sweeps on the receiving synth)
// Out over BLE-MIDI ("MURMUR" on her phone) and USB-MIDI. Touch UI: scale, key, sensitivity,
// voices, demo. ⛔ No human input to the music — the plant is the only musician (his rule).
//
// Build: firmware/build.sh  (arduino-cli, esp32 core, LovyanGFX).
#include <Preferences.h>
#include "USB.h"
#include "USBMIDI.h"
#include "board.h"
#include "blemidi.h"
#include "music.h"
#include "ota.h"

static board::LGFX* gfx = nullptr;
static LGFX_Sprite* frame = nullptr;
static USBMIDI usbMidi;
static Preferences prefs;

// ------------------------------------------------------------------ settings (persisted)
struct Settings {
  uint8_t scale = 0, root = 0, sens = 5, voices = 3, speed = 1;   // speed: wave scroll 0 slow 1 normal 2 fast
  bool demo = false, flip = false, wifi = true, bass = false;
} S;

static void load() {
  prefs.begin("murmur", true);
  S.scale = prefs.getUChar("scale", 0) % music::N_SCALES;
  S.root = prefs.getUChar("root", 0) % 12;
  S.sens = constrain(prefs.getUChar("sens", 5), 1, 9);
  S.voices = constrain(prefs.getUChar("voices", 3), 1, 5);
  S.demo = prefs.getBool("demo", false);
  S.flip = prefs.getBool("flip", false);
  S.wifi = prefs.getBool("wifi", true);
  S.bass = prefs.getBool("bass", false);
  S.speed = prefs.getUChar("speed", 1) % 3;
  prefs.end();
}
static void save() {
  prefs.begin("murmur", false);
  prefs.putUChar("scale", S.scale); prefs.putUChar("root", S.root);
  prefs.putUChar("sens", S.sens); prefs.putUChar("voices", S.voices);
  prefs.putBool("demo", S.demo); prefs.putBool("flip", S.flip); prefs.putBool("wifi", S.wifi);
  prefs.putBool("bass", S.bass);
  prefs.putUChar("speed", S.speed);
  prefs.end();
}

// ------------------------------------------------------------------ the plant's pulses
static volatile uint32_t ring[128];
static volatile uint32_t head = 0, lastEdgeUs = 0, lastPulseMs = 0;

// ⚠️ STORM GUARD: if IO17 toggles absurdly fast (a 555 at tens of kHz, or a floating wire
//   picking up noise) every edge is an interrupt and the main loop starves — the screen went
//   black with USB still up (2026-11-03). Edges are counted; past STORM_EDGES in a 100 ms
//   window the interrupt is DISABLED (ISR-safe), the screen says so, and loop() re-arms it.
static volatile uint32_t edgesTotal = 0, stormWinStart = 0, stormWinEdges = 0;
static volatile bool storm = false;
static const uint32_t STORM_EDGES = 2000;          // > 20 kHz sustained = not a plant
#include <driver/gpio.h>

static void IRAM_ATTR onEdge() {
  uint32_t t = micros();
  edgesTotal = edgesTotal + 1;
  if (t - stormWinStart > 100000) { stormWinStart = t; stormWinEdges = 0; }
  stormWinEdges = stormWinEdges + 1;
  if (stormWinEdges > STORM_EDGES) {
    gpio_intr_disable((gpio_num_t)board::SIGNAL_PIN);
    storm = true;
    return;
  }
  uint32_t p = t - lastEdgeUs;
  lastEdgeUs = t;
  if (p > 100) {  // ignore glitches under 100 µs
    ring[head & 127] = p;
    head = head + 1;
    lastPulseMs = millis();
  }
}

// once a second: the measured pulse rate, to the log and the screen
static uint32_t rateHz = 0, rateLastMs = 0, rateLastEdges = 0, stormSinceMs = 0;
static void rateTick() {
  uint32_t now = millis();
  if (now - rateLastMs < 1000) return;
  uint32_t e = edgesTotal;
  rateHz = (e - rateLastEdges) * 1000 / max((uint32_t)1, (uint32_t)(now - rateLastMs));
  rateLastEdges = e; rateLastMs = now;
  Serial.printf("rate %lu Hz%s demo=%d\n", (unsigned long)rateHz, storm ? " STORM(paused)" : "", S.demo);
  if (storm && !stormSinceMs) stormSinceMs = now;
  if (storm && now - stormSinceMs > 2000) {           // re-test every 2 s
    storm = false; stormSinceMs = 0; stormWinEdges = 0;
    gpio_intr_enable((gpio_num_t)board::SIGNAL_PIN);
  }
}

// demo: a pretend plant — a level that WANDERS and SETTLES (mean-reverting), a slowly moving
// resting point, and now and then a "mood" (a jump that fades). ~40 pulses/s.
static uint32_t demoNextMs = 0;
static float demoLevel = 25000, demoRest = 25000, demoMood = 0;
static void demoTick() {
  if (millis() < demoNextMs) return;
  demoRest = constrain(demoRest + random(-100, 101) * 0.8f, 18000.0f, 32000.0f);
  if (random(0, 250) == 0) demoMood += random(-1500, 1501);
  demoMood *= 0.985f;
  demoLevel += (demoRest + demoMood - demoLevel) * 0.04f + random(-100, 101) * 1.5f;
  uint32_t p = (uint32_t)(demoLevel + random(-40, 41));
  ring[head & 127] = p;
  head = head + 1;
  lastPulseMs = millis();
  demoNextMs = millis() + p / 1000;
}

// ------------------------------------------------------------------ MIDI out (BLE + USB)
static bool usbUp = false;
static void midi(uint8_t status, uint8_t d1, uint8_t d2) {
  blemidi::send(status, d1, d2);
  if (usbUp) {
    uint8_t cmd = status & 0xF0, ch = (status & 0x0F) + 1;
    if (cmd == 0x90) usbMidi.noteOn(d1, d2, ch);
    else if (cmd == 0x80) usbMidi.noteOff(d1, d2, ch);
    else if (cmd == 0xB0) usbMidi.controlChange(d1, d2, ch);
  }
}

struct Voice { uint8_t note, ch; uint32_t offAt; bool on; };
static Voice voices[5];
static bool plantPresent();

// the bass drone: her key's root + fifth, low, held on MIDI CHANNEL 2 (its own instrument) —
//   root and fifth together, like a tanpura under a sitar
static uint8_t droneNote = 0;
static bool droneOn = false;
static uint32_t droneAt = 0;
static void droneOff() { if (droneOn) { midi(0x81, droneNote, 0); midi(0x81, droneNote + 7, 0); droneOn = false; } }

struct Pending { uint8_t note, vel; uint32_t len, at; bool used; };
static Pending pend[8];               // arpeggio notes waiting their turn
static void allOff() {
  for (auto& v : voices) if (v.on) { midi(0x80 | v.ch, v.note, 0); v.on = false; }
  for (auto& q : pend) q.used = false;
  droneOff();
}
static void play(uint8_t note, uint8_t vel, uint32_t lenMs) {
  for (int i = 0; i < 5; i++)              // same note already sounding: restrike it, don't stack
    if (voices[i].on && voices[i].note == note) { midi(0x80, note, 0); voices[i].on = false; }
  int free = -1, oldest = 0;
  for (int i = 0; i < S.voices; i++) {
    if (!voices[i].on) { free = i; break; }
    if (voices[i].offAt < voices[oldest].offAt) oldest = i;
  }
  if (free < 0) { midi(0x80, voices[oldest].note, 0); free = oldest; }
  midi(0x90, note, vel);
  voices[free] = {note, 0, millis() + lenMs, true};
}
static void later(uint8_t note, uint8_t vel, uint32_t len, uint32_t inMs) {
  for (auto& q : pend) if (!q.used) { q = {note, vel, len, millis() + inMs, true}; return; }
}
static void voiceTick() {
  uint32_t now = millis();
  for (auto& q : pend) if (q.used && now >= q.at) { q.used = false; play(q.note, q.vel, q.len); }
  for (int i = 0; i < 5; i++)
    if (voices[i].on && (now >= voices[i].offAt || i >= S.voices)) {
      midi(0x80 | voices[i].ch, voices[i].note, 0);
      voices[i].on = false;
    }
}

// ------------------------------------------------------------------ listening
// ★ THE MUSIC ENGINE (v3, 2026-11-04). Every 10 pulses = one window mean m.
//   FAST — the window-to-window change: unusual for THIS plant right now (x calm..chatty) = a note.
//     direction of the change -> the melody steps UP or DOWN the scale; size of the change -> how far
//     (step, skip, leap). It never repeats the same note twice running.
//     WHERE m sits among its last 32 readings (RANK, not min/max: one outlier can't squash the rest
//     against the root) -> a home the melody is gently pulled back toward.
//     STRENGTH -> how many notes: a nudge = one note, more = a two-note interval, strong = a spread
//     chord with its bass an octave down, very strong = the chord ARPEGGIATED (plus its 7th).
//     sparse..full caps it: at 1 voice it's always a single melody.
//   SLOW — a long average of m:
//     where it sits in the last few minutes -> the REGISTER (low / middle / high octave).
//     sustained drift -> the KEY walks the circle of fifths (rising = up a fifth, falling = down),
//     at most 3 steps from her key, and wanders home when the plant settles.
//   BIG EVENT (a jolt far past anything usual) -> the mood tips to its sister for ~25 s.
static const int WIN = 10;
static uint32_t tail = 0;
static float win[WIN];
static int nwin = 0;
static float prevMean = 0, typical = 0;  // typical = how much the plant USUALLY moves per window
static bool primed = false;
static uint32_t winStartMs = 0, lastCcMs = 0;
static int lastCc = -1;
static uint8_t lastNote = 0, lastVel = 0;
static uint32_t lastNoteMs = 0;
static bool bloomPending = false;   // a note just played: bloom once, at the wave's leading edge
static const int HIST = 32;               // recent window means: the plant's current range
static float hist[HIST];
static int nhist = 0;

static float slow = 0;                    // the long average
static const int LHIST = 30;              // slow, sampled every 10 windows: the last few minutes
static float lhist[LHIST];
static int nlhist = 0, regShift = 0;
static int keyFifths = 0;                 // steps round the circle of fifths from her key
static float keyAnchor = 0;
static uint32_t keyMs = 0;
static int moodTemp = -1;                 // sister mood in force, or -1
static uint32_t moodUntil = 0, moodMs = 0;
static int curDeg = 0, curN = 5;          // the melody's position in the scale

// ★ SWELL -> CC11 (expression) on channel 1: a jolt pushes the volume up at once, then it eases
//   back over ~4 s as the plant settles — the same attack-and-backoff the note density has.
static float swell = 0;
static int lastExpr = -1;
static uint32_t swellMs = 0, exprMs = 0;
static void swellHit(float e) {
  swell = max(swell, min(1.0f, 0.25f + (e - 1) / 3));
  int x = 70 + (int)(57 * swell);                  // send the attack NOW, ahead of the note
  if (x != lastExpr) { midi(0xB0, 11, x); lastExpr = x; exprMs = millis(); }
}
static void swellTick() {
  uint32_t now = millis();
  if (now - swellMs < 50) return;
  swell *= expf(-(now - swellMs) / 4000.0f);
  swellMs = now;
  int x = 70 + (int)(57 * swell);
  if (abs(x - lastExpr) >= 2 && now - exprMs > 100) { midi(0xB0, 11, x); lastExpr = x; exprMs = now; }
}

static float dbgMean = 0, dbgRatio = 0, dbgChange = 0;   // last window, for /status
static uint32_t notesTotal = 0;

static int activeScale() { return moodTemp >= 0 && millis() < moodUntil ? moodTemp : S.scale; }
static int activeRoot() { return S.root + music::fifths(keyFifths); }

static float rankIn(const float* a, int n, float v) {   // 0..1: share of a[] below v (ties half)
  if (n < 2) return 0.5f;
  float below = 0;
  for (int k = 0; k < n; k++) below += a[k] < v ? 1 : a[k] == v ? 0.5f : 0;
  return below / n;
}

static const int TRACE_W = 240;
static float trace[TRACE_W];               // raw periods (the screen auto-scales)
static bool traceMark[TRACE_W];
static int traceHead = 0;

// how unusual a change must be (x its typical change) to become a note: 1 = calm ... 9 = chatty
//   ⚠️ must stay > 1 at chatty: at 0.8 (the old 9) it fired on the plant's ORDINARY movement —
//   half of all windows played ("balls out hyper sample mode", 2026-11-04, apple at 180 Hz).
static float sensFactor() { return 3.5f - (S.sens - 1) * 0.275f; }   // 1 -> 3.5x ... 9 -> 1.3x
static uint32_t noteGapMs() { return 120 + (9 - S.sens) * 25; }       // chatty 120 ms ... calm 320 ms
// ★ NOISE FLOOR: the ISR's timing jitter (BLE + Wi-Fi interrupts) moves a 10-pulse mean by a few µs
//   no matter what the plant does. Measured 2026-11-04 at 180 Hz: 'typical' sat at 2-4.7 µs. At low
//   rates the relative floor (0.05%) is far above it; at high rates jitter IS the signal. Floor it.
static const float JITTER_US = 6.0f;

static void slowTick(float m) {
  slow = slow == 0 ? m : slow + (m - slow) * 0.02f;
  static int every = 0;
  if (++every < 10) return;
  every = 0;
  lhist[nlhist % LHIST] = slow; nlhist++;
  // register, with hysteresis so it doesn't flicker between octaves
  float r = rankIn(lhist, min(nlhist, LHIST), slow);
  if (nlhist >= 6) {
    if (r < 0.2f) regShift = -1; else if (r > 0.8f) regShift = 1;
    else if (r > 0.35f && r < 0.65f) regShift = 0;
  }
  // key: sustained drift since the last change walks a fifth; quiet for 3 min walks home
  uint32_t now = millis();
  if (keyAnchor == 0) { keyAnchor = slow; keyMs = now; }
  float drift = slow - keyAnchor;
  if (now - keyMs > 40000 && fabsf(drift) > max(keyAnchor * 0.025f, typical * 40)) {
    int dir = drift > 0 ? 1 : -1;
    if (abs(keyFifths + dir) <= 3) keyFifths += dir;
    keyAnchor = slow; keyMs = now;
    Serial.printf("key -> %s (%+d fifths)\n", music::KEYS[(activeRoot() % 12 + 12) % 12], keyFifths);
  } else if (keyFifths != 0 && now - keyMs > 180000) {
    keyFifths += keyFifths > 0 ? -1 : 1;
    keyAnchor = slow; keyMs = now;
  }
}

// ★ the wave scrolls by TIME, not by pulse: one point per 40 ms (240 px = ~10 s on screen) at any
//   rate. Per-pulse it raced 7x faster when an apple went from 25 Hz to 180 Hz (2026-11-04).
static float traceAcc = 0;
static int traceN = 0;
static bool traceNoteDue = false;
static uint32_t traceMs = 0, speedShownMs = 0;
static const uint16_t TRACE_STEP_MS[3] = {100, 40, 15};     // ~24 s · ~10 s · ~4 s across the screen
static const char* SPEED_NAME[3] = {"slow wave", "normal wave", "fast wave"};
static void traceTick() {
  if (millis() - traceMs < TRACE_STEP_MS[S.speed]) return;
  traceMs = millis();
  if (!traceN) return;                     // no pulses: hold still, don't invent points
  trace[traceHead] = traceAcc / traceN;
  traceMark[traceHead] = traceNoteDue;
  traceHead = (traceHead + 1) % TRACE_W;
  traceAcc = 0; traceN = 0; traceNoteDue = false;
}

static void onPeriod(float p) {
  traceAcc += p; traceN++;
  win[nwin++] = p;
  if (nwin < WIN) return;
  nwin = 0;
  float m = 0;
  for (float x : win) m += x;
  m /= WIN;
  uint32_t winMs = millis() - winStartMs;
  winStartMs = millis();
  hist[nhist % HIST] = m;
  nhist++;
  if (!primed) { prevMean = m; typical = m * 0.002f; slow = 0; primed = true; return; }

  float change = m - prevMean;
  prevMean = m;
  // ★ ADAPTIVE: steady drift raises "typical" by itself, so drift alone stops making notes;
  //   only a change that is unusual FOR THIS PLANT, RIGHT NOW, plays.
  float ratio = fabsf(change) / max(max(typical, m * 0.0005f), JITTER_US);
  typical += (fabsf(change) - typical) * 0.05f;
  dbgMean = m; dbgRatio = ratio; dbgChange = change;
  slowTick(m);

  float pos = rankIn(hist, min(nhist, HIST), m);   // rank, not min/max
  float sf = sensFactor();

  if (ratio > sf && millis() - lastNoteMs > noteGapMs()) {
    float e = ratio / sf;                            // 1 = just enough ... big = a jolt
    swellHit(e);
    if (e > 5 && millis() - moodMs > 60000) {        // a big event tips the mood for a while
      moodTemp = music::SISTER[S.scale]; moodUntil = millis() + 25000; moodMs = millis();
      Serial.printf("mood -> %s\n", music::SCALES[moodTemp].mood);
    }
    const auto& sc = music::SCALES[activeScale()];
    int n = sc.n;
    if (n != curN) { curDeg = curDeg * n / curN; curN = n; }   // mood changed size: same height
    int dir = change > 0 ? 1 : -1;
    int step = e < 1.6f ? 1 : e < 2.5f ? 2 : e < 4 ? 3 : 4;
    curDeg += dir * step;
    int home = (int)lroundf(pos * 2 * n) - n / 2;              // where the level says it should be
    if (curDeg - home > n) curDeg--;
    if (home - curDeg > n) curDeg++;
    if (curDeg > 2 * n) curDeg = 2 * n - 1;                    // bounce off the ends
    if (curDeg < -n) curDeg = -n + 1;
    int root = activeRoot(), oct = 3 + regShift;
    uint8_t note = music::note(sc, curDeg, root, oct);
    if (note == lastNote) {                                    // never the same note twice running
      curDeg += (curDeg + dir > 2 * n || curDeg + dir < -n) ? -dir : dir;
      note = music::note(sc, curDeg, root, oct);
    }
    uint8_t vel = (uint8_t)constrain(55 + 30 * (ratio - sf), 45, 120);
    uint32_t len = constrain(winMs * 4, 180u, 1600u);
    int size = e < 1.5f ? 1 : e < 2.2f ? 2 : e < 3.5f ? 3 : 4;  // how many notes this change earns
    size = min(size, (int)S.voices);
    uint8_t sub = (uint8_t)max(40, vel - 18);
    if (size >= 2 && size < 4) play(music::note(sc, curDeg - 2, root, oct), sub, len);   // a third below
    if (size == 3) play(music::note(sc, curDeg - 4 - n, root, oct), sub, len * 3 / 2);   // bass, octave down
    if (size >= 4) {                                           // arpeggio: bass, 1, 3, 5, 7 rising
      play(music::note(sc, curDeg - n, root, oct), sub, len * 2);
      int sv = min((int)S.voices - 1, 4);
      for (int k = 0; k < sv; k++)
        later(music::note(sc, curDeg + 2 * k, root, oct), k ? sub : vel, len, 110 * (k + 1));
    } else {
      play(note, vel, len);
    }
    lastNote = note; lastVel = vel; lastNoteMs = millis(); notesTotal++;
    traceNoteDue = true;                    // the seed lands on the next wave point
    bloomPending = true;
  }
  int cc = (int)constrain(pos * 127, 0, 127);
  if (abs(cc - lastCc) >= 2 && millis() - lastCcMs > 100) {
    midi(0xB0, 74, cc);
    lastCc = cc; lastCcMs = millis();
  }
}

// the drone (root + fifth) follows the key; restruck every 12 s so decaying patches keep sounding
static void droneTick() {
  if (!S.bass || !plantPresent()) { droneOff(); return; }
  uint8_t want = (uint8_t)(36 + ((activeRoot() % 12) + 12) % 12);   // C2..B2
  if (droneOn && want == droneNote && millis() - droneAt < 12000) return;
  droneOff();
  midi(0x91, want, 50);
  midi(0x91, want + 7, 40);
  droneNote = want; droneOn = true; droneAt = millis();
}

// ⚠️ needs at least one REAL pulse: lastPulseMs starts at 0, so for the first 1.5 s after boot
//   'millis() - 0 < 1500' said a plant was there with no data — the wave then auto-scaled an empty
//   trace, divided by zero and looped ~2^31 pixels: the black screen of 2026-11-03.
static bool plantPresent() { return lastPulseMs != 0 && millis() - lastPulseMs < 1500; }

// ------------------------------------------------------------------ screen
// ★ For Jeanne, who is not an audio person: no jargon on the main screen. Scale is a MOOD, the
//   sensitivity is "calm ... chatty", voices are "sparse ... full". Key, the pretend plant and
//   "how to listen" live behind the gear. Botanical palette; notes BLOOM on the stage.
static uint16_t C_BG, C_PANEL, C_CREAM, C_SAGE, C_LEAF, C_DIM, C_PEACH, C_LINE;
static void palette() {
  C_BG = gfx->color565(12, 22, 17);       // deep forest
  C_PANEL = gfx->color565(22, 38, 30);    // moss panel
  C_CREAM = gfx->color565(242, 233, 216);
  C_SAGE = gfx->color565(143, 185, 150);
  C_LEAF = gfx->color565(95, 175, 110);
  C_DIM = gfx->color565(90, 120, 102);
  C_PEACH = gfx->color565(244, 162, 97);
  C_LINE = gfx->color565(40, 64, 50);
}
static uint16_t lerp565(uint16_t a, uint16_t b, float t) {
  t = constrain(t, 0.0f, 1.0f);
  int ar = (a >> 11) & 31, ag = (a >> 5) & 63, ab = a & 31, br = (b >> 11) & 31, bg = (b >> 5) & 63, bb = b & 31;
  return ((int)(ar + (br - ar) * t) << 11) | ((int)(ag + (bg - ag) * t) << 5) | (int)(ab + (bb - ab) * t);
}

static void rotate() {
  gfx->setRotation(S.flip ? 1 : 3);  // portrait, USB edge up (checked on the board 2026-11-02)
}

// blooms: every note opens a ring on the stage that grows and fades
struct Bloom { int16_t x, y; uint32_t born; uint8_t vel; };
static Bloom blooms[10];
static int bloomNext = 0;
static void bloom(int x, int y, uint8_t vel) { blooms[bloomNext] = {(int16_t)x, (int16_t)y, millis(), vel}; bloomNext = (bloomNext + 1) % 10; }

static bool settingsOpen = false;
static const int ST_X = 6, ST_Y = 38, ST_W = 228, ST_H = 158;   // the stage

static void dots(int cx, int y, int filled, int total) {
  for (int i = 0; i < total; i++) {
    int x = cx + (i - (total - 1) / 2.0f) * 16;
    if (i < filled) frame->fillCircle(x, y, 5, C_SAGE);
    else frame->drawCircle(x, y, 5, C_DIM);
  }
}

static void gear(int cx, int cy, uint16_t c) {
  for (int k = 0; k < 8; k++) {
    float a = k * PI / 4;
    frame->fillCircle(cx + cosf(a) * 7, cy + sinf(a) * 7, 2, c);
  }
  frame->fillCircle(cx, cy, 6, c);
  frame->fillCircle(cx, cy, 3, C_BG);
}

// status icons (header): bright = connected, dim = waiting, dark + slash = switched off
static void iconBle(int x, int y, uint16_t c) {
  for (int o = 0; o < 2; o++) {           // 2 px strokes
    frame->drawLine(x + o, y - 7, x + o, y + 7, c);
    frame->drawLine(x + o, y - 7, x + 4 + o, y - 3, c);
    frame->drawLine(x + 4 + o, y - 3, x - 4 + o, y + 4, c);
    frame->drawLine(x + o, y + 7, x + 4 + o, y + 3, c);
    frame->drawLine(x + 4 + o, y + 3, x - 4 + o, y - 4, c);
  }
}
static void iconWifi(int x, int y, uint16_t c, bool off) {
  frame->fillCircle(x, y + 6, 2, c);
  frame->fillArc(x, y + 6, 6, 4, 225, 315, c);
  frame->fillArc(x, y + 6, 11, 9, 225, 315, c);
  if (off) { frame->drawLine(x - 8, y - 6, x + 8, y + 8, C_DIM); frame->drawLine(x - 7, y - 6, x + 9, y + 8, C_DIM); }
}

static int dbgFrames = 0;
#define DBG(t) do { if (dbgFrames < 2) { Serial.println(t); Serial.flush(); } } while (0)
static void drawMain() {
  frame->fillScreen(C_BG);
  DBG("m0");
  // wordmark + status
  frame->setFont(&fonts::Orbitron_Light_24);
  frame->setTextColor(C_CREAM);
  frame->setTextDatum(middle_left);
  frame->drawString("MURMUR", 10, 18);
  gear(222, 18, C_DIM);
  iconBle(198, 18, blemidi::connected ? C_LEAF : C_DIM);
  bool wifiUp = S.wifi && WiFi.status() == WL_CONNECTED;
  iconWifi(176, 16, wifiUp ? C_LEAF : S.wifi ? C_DIM : C_LINE, !S.wifi);

  DBG("m1");
  // the stage: the plant's signal as a soft filled wave
  frame->fillRoundRect(ST_X, ST_Y, ST_W, ST_H, 14, C_PANEL);
  const int bottom = ST_Y + ST_H - 8;
  bool alive = plantPresent();
  if (alive) {
    const int n = ST_W - 16, top = ST_Y + 26;
    float lo = 1e9, hi = -1e9;
    for (int i = 0; i < n; i++) {
      float v = trace[(traceHead + TRACE_W - n + i) % TRACE_W];
      if (v > 0) { lo = min(lo, v); hi = max(hi, v); }
    }
    if (hi < lo) hi = lo = 1.0f;                            // no samples at all: flat, never NaN
    float span = max(max(hi - lo, (hi + lo) * 0.0015f), 1.0f);  // never magnify noise, never /0
    float c = (hi + lo) / 2;
    int ys[ST_W];
    for (int i = 0; i < n; i++) {                           // 5-point smoothing: let it flow
      float acc = 0; int k = 0;
      for (int d = -2; d <= 2; d++) {
        int j2 = i + d;
        if (j2 < 0 || j2 >= n) continue;
        float v = trace[(traceHead + TRACE_W - n + j2) % TRACE_W];
        acc += v > 0 ? v : c; k++;
      }
      float v = acc / k;
      ys[i] = constrain(top + (int)((1.0f - ((v - c) / span + 0.5f)) * (bottom - 18 - top)), top, bottom - 1);
    }
    for (int i = 0; i < n; i++) {
      int x = ST_X + 8 + i, y = ys[i];
      for (int yy = y; yy < bottom; yy++)
        frame->drawPixel(x, yy, lerp565(C_LEAF, C_PANEL, (float)(yy - y) / (bottom - y + 1) * 1.2f));
      frame->drawPixel(x, y, C_SAGE);
      frame->drawPixel(x, y - 1, C_SAGE);
    }
    for (int i = 0; i < n; i++)                             // the notes, as seeds on the wave
      if (traceMark[(traceHead + TRACE_W - n + i) % TRACE_W]) frame->fillCircle(ST_X + 8 + i, ys[i] - 1, 2, C_PEACH);
    if (bloomPending) { bloom(ST_X + 8 + n - 1, ys[n - 1], lastVel); bloomPending = false; }
  }
  DBG("m2");
  frame->setClipRect(ST_X + 2, ST_Y + 2, ST_W - 4, ST_H - 4);   // blooms stay on the stage
  for (auto& b : blooms) {
    if (!b.born) continue;
    float t = (millis() - b.born) / 1400.0f;
    if (t >= 1) { b.born = 0; continue; }
    int r = 4 + (int)(t * (18 + b.vel / 4));
    uint16_t c = lerp565(C_PEACH, C_PANEL, t);
    frame->drawCircle(b.x, b.y, r, c);
    frame->drawCircle(b.x, b.y, r + 1, c);
    if (t < 0.25f) frame->fillCircle(b.x, b.y, 3, C_PEACH);
  }
  frame->clearClipRect();
  DBG("m3");
  frame->setFont(&fonts::FreeSans9pt7b);
  frame->setTextDatum(middle_center);
  if (storm || (stormSinceMs && millis() - stormSinceMs < 2500)) {
    frame->setTextColor(C_PEACH);
    frame->drawString("signal too fast", 120, ST_Y + ST_H / 2 - 8);
    frame->setTextColor(C_DIM);
    frame->drawString("check the 555 wiring", 120, ST_Y + ST_H / 2 + 14);
  } else if (!alive) {
    frame->setTextColor(C_SAGE);
    frame->drawString(S.demo ? "waking the pretend plant..." : "clip the leads to a leaf", 120, ST_Y + ST_H / 2 - 8);
    frame->setTextColor(C_DIM);
    frame->drawString(S.demo ? "" : "and give it a moment", 120, ST_Y + ST_H / 2 + 14);
  } else {
    // where the plant has taken the music: key (walks the circle of fifths), and a tipped mood
    frame->setTextColor(keyFifths || activeScale() != S.scale ? C_PEACH : C_DIM);
    frame->setTextDatum(top_left);
    String k = String("in ") + music::KEYS[(activeRoot() % 12 + 12) % 12];
    if (activeScale() != S.scale) k += String(" - ") + music::SCALES[activeScale()].mood;
    frame->drawString(k, ST_X + 10, ST_Y + 8);
    if (speedShownMs && millis() - speedShownMs < 1500) {        // just tapped: say the new speed
      frame->setTextColor(C_CREAM);
      frame->setTextDatum(top_right);
      frame->drawString(SPEED_NAME[S.speed], ST_X + ST_W - 10, ST_Y + 8);
    } else if (millis() - lastNoteMs < 2500 && lastNoteMs) {
      frame->setTextColor(C_DIM);
      frame->setTextDatum(top_right);
      frame->drawString(music::name(lastNote), ST_X + ST_W - 10, ST_Y + 8);
    }
  }

  DBG("m4");
  // one friendly line: what to do / what is happening
  frame->setTextDatum(middle_center);
  frame->setTextColor(blemidi::connected ? C_LEAF : C_DIM);
  frame->drawString(blemidi::connected ? "playing on your phone" : "open GarageBand to listen", 120, 206);

  DBG("m5");
  // MOOD
  frame->fillRoundRect(6, 220, 228, 34, 12, C_PANEL);
  frame->setTextColor(C_DIM);
  frame->setFont(&fonts::FreeSansBold12pt7b);
  frame->drawString("<", 22, 237);
  frame->drawString(">", 218, 237);
  frame->setFont(&fonts::Satisfy_24);
  frame->setTextColor(C_CREAM);
  frame->drawString(music::SCALES[S.scale].mood, 120, 236);

  DBG("m6");
  // calm ... chatty
  frame->fillRoundRect(6, 258, 228, 28, 12, C_PANEL);
  frame->setFont(&fonts::FreeSans9pt7b);
  frame->setTextColor(C_DIM);
  frame->setTextDatum(middle_left);  frame->drawString("calm", 14, 272);
  frame->setTextDatum(middle_right); frame->drawString("chatty", 226, 272);
  dots(120, 272, (S.sens + 1) / 2, 5);

  DBG("m7");
  // sparse ... full
  frame->fillRoundRect(6, 290, 228, 28, 12, C_PANEL);
  frame->setTextDatum(middle_left);  frame->drawString("sparse", 14, 304);
  frame->setTextDatum(middle_right); frame->drawString("full", 226, 304);
  dots(120, 304, S.voices, 5);
}

static void drawSettings() {
  frame->fillScreen(C_BG);
  frame->setFont(&fonts::Orbitron_Light_24);
  frame->setTextColor(C_CREAM);
  frame->setTextDatum(middle_left);
  frame->drawString("settings", 10, 18);
  frame->setFont(&fonts::FreeSans9pt7b);

  auto row = [](int y, const char* label, const String& value) {
    frame->fillRoundRect(6, y, 228, 30, 12, C_PANEL);
    frame->setTextColor(C_DIM);
    frame->setTextDatum(middle_left);
    frame->drawString(label, 16, y + 15);
    frame->setTextColor(C_CREAM);
    frame->setTextDatum(middle_right);
    frame->drawString(value, 222, y + 15);
  };
  row(34, "key", String("<  ") + music::KEYS[S.root] + "  >");
  row(68, "bass drone", S.bass ? "on" : "off");
  row(102, "pretend plant", S.demo ? "on" : "off");
  row(136, "turn screen", "flip");
  row(170, "wifi (updates)", S.wifi ? "on" : "off");
  frame->setTextDatum(top_right);
  frame->setTextColor(C_LINE);
  frame->drawString(ota::ip(), 232, 6);

  frame->setTextDatum(top_left);
  frame->setTextColor(C_SAGE);
  frame->drawString("to listen on an iPhone:", 12, 206);
  frame->setTextColor(C_DIM);
  frame->drawString("GarageBand > settings > advanced", 12, 222);
  frame->drawString("> bluetooth MIDI > MURMUR", 12, 238);
  frame->drawString("bass drone plays on MIDI ch 2", 12, 258);

  frame->fillRoundRect(60, 284, 120, 32, 16, C_LEAF);
  frame->setTextColor(C_BG);
  frame->setTextDatum(middle_center);
  frame->setFont(&fonts::FreeSansBold12pt7b);
  frame->drawString("done", 120, 300);
}

static void draw() {
  if (settingsOpen) drawSettings(); else drawMain();
  DBG("push");
  frame->pushSprite(0, 0);
  DBG("pushed");
  dbgFrames++;
}

static bool wasDown = false;
static void touch() {
  uint16_t x, y;
  uint32_t tt = millis();
  static int tdbg = 0;
  if (tdbg < 3) { Serial.println("touch: read..."); Serial.flush(); }
  bool down = gfx->getTouch(&x, &y);
  if (tdbg < 3) { Serial.printf("touch: back (%d)\n", down); Serial.flush(); tdbg++; }
  if (millis() - tt > 100) Serial.printf("SLOW touch read: %lu ms\n", (unsigned long)(millis() - tt));
  // ⚠️ this panel's touch is MIRRORED in x relative to the display (measured 2026-11-03: corner
  //   taps logged TL 231,28 · TR 4,32 · BL 229,319 · BR 21,316 — x reversed, y right).
  if (down) x = (gfx->width() - 1) - x;
  if (down && !wasDown) {
    Serial.printf("touch %u,%u %s\n", x, y, settingsOpen ? "settings" : "main");   // calibration log
    if (settingsOpen) {
      if (y >= 34 && y < 66) { if (x < 160) S.root = (S.root + 11) % 12; else S.root = (S.root + 1) % 12; keyFifths = 0; }
      else if (y >= 68 && y < 100) { S.bass = !S.bass; }
      else if (y >= 102 && y < 134) { S.demo = !S.demo; allOff(); primed = false; }
      else if (y >= 136 && y < 168) { S.flip = !S.flip; rotate(); }
      else if (y >= 170 && y < 202) { S.wifi = !S.wifi; ota::enable(S.wifi); }
      else if (y >= 270) settingsOpen = false;
    } else {
      if (y < 50 && x > 170) settingsOpen = true;                       // the gear
      else if (y >= ST_Y && y < ST_Y + ST_H) { S.speed = (S.speed + 1) % 3; speedShownMs = millis(); }   // tap the wave: its speed
      else if (y >= 220 && y < 256) {                                    // mood
        if (x < 120) S.scale = (S.scale + music::N_SCALES - 1) % music::N_SCALES;
        else S.scale = (S.scale + 1) % music::N_SCALES;
      } else if (y >= 258 && y < 288) {                                  // calm ... chatty
        if (x < 120 && S.sens > 1) S.sens = max(1, S.sens - 2);
        if (x >= 120 && S.sens < 9) S.sens = min(9, S.sens + 2);
      } else if (y >= 290) {                                             // sparse ... full
        if (x < 120 && S.voices > 1) S.voices--;
        if (x >= 120 && S.voices < 5) S.voices++;
      }
    }
    save();
  }
  wasDown = down;
}

// ------------------------------------------------------------------ main
void setup() {
  Serial.begin(115200);   // USB CDC alongside MIDI: logs, and the 1200-baud touch for re-flashing
  for (uint32_t t0 = millis(); !Serial && millis() - t0 < 3000;) delay(10);   // let a logger attach
  Serial.println("stage: boot");
  ota::rollbackCheck();      // 3 failed boots in a row -> previous firmware slot
  Serial0.begin(115200);  // and the UART port too
  load();
  USB.productName("MURMUR");
  USB.manufacturerName("MURMUR");
  usbMidi.begin();
  USB.begin();
  usbUp = true;

  Serial.println("stage: touch probe"); Serial.flush();
  board::Touch t = board::probe();
  Serial.printf("MURMUR: touch %s\n", t == board::Touch::FT6336 ? "FT6336" : t == board::Touch::GT911 ? "GT911" : "none");
  Serial.println("stage: gfx init"); Serial.flush();
  gfx = new board::LGFX(t);
  gfx->init();
  Serial.println("stage: gfx ok"); Serial.flush();
  rotate();
  pinMode(board::BACKLIGHT, OUTPUT);
  digitalWrite(board::BACKLIGHT, HIGH);
  palette();
  frame = new LGFX_Sprite(gfx);
  frame->setPsram(true);
  frame->setColorDepth(16);
  frame->createSprite(240, 320);

  if (S.wifi) ota::begin();  // Wi-Fi joins in the background; updates come from talos
  ota::screen = []() -> const uint8_t* { return frame ? (const uint8_t*)frame->getBuffer() : nullptr; };
  ota::statusExtra = []() -> String {
    return String(",\"rate_hz\":") + rateHz + ",\"plant\":" + (plantPresent() ? "true" : "false") +
           ",\"demo\":" + (S.demo ? "true" : "false") + ",\"bt\":" + (blemidi::connected ? "true" : "false") +
           ",\"mood\":\"" + music::SCALES[S.scale].mood + "\",\"sens\":" + S.sens + ",\"voices\":" + S.voices +
           ",\"key\":\"" + music::KEYS[(activeRoot() % 12 + 12) % 12] + "\",\"fifths\":" + keyFifths +
           ",\"active_mood\":\"" + music::SCALES[activeScale()].mood + "\",\"register\":" + regShift +
           ",\"bass\":" + (S.bass ? "true" : "false") +
           ",\"mean_us\":" + String(dbgMean, 1) + ",\"typical_us\":" + String(typical, 2) +
           ",\"change_us\":" + String(dbgChange, 2) + ",\"ratio\":" + String(dbgRatio, 2) +
           ",\"notes\":" + notesTotal;
  };
  Serial.println("stage: ble"); Serial.flush();
  blemidi::begin("MURMUR");
  Serial.println("stage: irq"); Serial.flush();
  pinMode(board::SIGNAL_PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(board::SIGNAL_PIN), onEdge, RISING);
  winStartMs = millis();
  Serial.printf("settings: scale=%u root=%u sens=%u voices=%u demo=%d flip=%d\n", S.scale, S.root, S.sens, S.voices, S.demo, S.flip);
  Serial.println("stage: setup done"); Serial.flush();
}

// debug over USB serial (for checking the screen from talos): 's' = dump the framebuffer
// (raw RGB565, 240x320, as stored in the sprite), 'D' = toggle the pretend plant.
static void debugPort() {
  while (Serial.available()) {
    int c = Serial.read();
    if (c == 's' && frame) {
      Serial.write((const uint8_t*)"SHOT", 4);
      Serial.write((const uint8_t*)frame->getBuffer(), 240 * 320 * 2);
      Serial.flush();
    } else if (c == 'S') {
      settingsOpen = !settingsOpen;
    } else if (c == 'D') {
      S.demo = !S.demo; allOff(); primed = false; save();
    }
  }
}

void loop() {
  ota::tick();
  static uint32_t loops = 0;
  if (loops++ < 3) { Serial.printf("stage: loop %lu\n", (unsigned long)loops); Serial.flush(); }
  debugPort();
  rateTick();
  if (S.demo) demoTick();
  while (tail != head) {
    if (head - tail > 128) tail = head - 128;  // fell behind: keep the newest
    onPeriod((float)ring[tail & 127]);
    tail++;
  }
  if (!plantPresent()) allOff();
  traceTick();
  voiceTick();
  droneTick();
  swellTick();
  touch();
  static uint32_t lastDraw = 0;
  if (millis() - lastDraw > 66) {
    static int ddbg = 0;
    if (ddbg < 3) { Serial.println("draw..."); Serial.flush(); }
    draw(); lastDraw = millis();
    if (ddbg < 3) { Serial.println("draw: done"); Serial.flush(); ddbg++; }
  }
}
