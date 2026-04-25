/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0.
 * To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */
#include <Arduino.h>
#include <string.h>
#include "settings.h"
#include "ir_signal.h"
#include "opt_sensor.h"

#define bitclr(reg, bit) (reg &= ~(1 << bit))
#define bittst(reg, bit) (reg & (1 << bit))

#ifdef BLUR_REDUCTION_FIRMWARE

#ifndef BLUR_PHASE_MODE_ALL
#define BLUR_PHASE_MODE_ALL 0
#endif
#ifndef BLUR_PHASE_MODE_AUTO
#define BLUR_PHASE_MODE_AUTO 1
#endif
#ifndef BLUR_PHASE_MODE_MANUAL_0
#define BLUR_PHASE_MODE_MANUAL_0 2
#endif
#ifndef BLUR_PHASE_MODE_MANUAL_1
#define BLUR_PHASE_MODE_MANUAL_1 3
#endif
#ifndef BLUR_PHASE_BRIGHTNESS_CHANGE_THRESHOLD_DEFAULT
#define BLUR_PHASE_BRIGHTNESS_CHANGE_THRESHOLD_DEFAULT 8
#endif
#ifndef BLUR_PHASE_SCORE_MARGIN_DEFAULT
#define BLUR_PHASE_SCORE_MARGIN_DEFAULT 16
#endif
#ifndef BLUR_PHASE_SCORE_DECAY_SHIFT
#define BLUR_PHASE_SCORE_DECAY_SHIFT 4
#endif
#endif

#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
volatile uint8_t ir_led_token_active_countdown = 0;
#endif

#ifdef OPT_SENSOR_ENABLE_STATS
uint32_t opt_sensor_stats_count = 0;
#endif

uint32_t opt_sensor_current_time;

#ifdef OPT_SENSOR_ENABLE_STREAM_READINGS_TO_SERIAL
uint8_t opt_sensor_enable_stream_readings_to_serial = 0;
#endif

uint8_t opt_sensor_enable_frequency_analysis_based_duplicate_frame_detection = 0;
uint8_t opt_sensor_enable_ignore_during_ir = 0;
uint8_t opt_sensor_enable_duplicate_realtime_reporting = 0;
uint8_t opt_sensor_output_stats = 0;

#ifdef BLUR_REDUCTION_FIRMWARE
uint8_t opt_sensor_detection_threshold_high = BLUR_OPT_SENSOR_DIP_DELTA_DEFAULT;
uint8_t opt_sensor_detection_threshold_low = BLUR_OPT_SENSOR_DIP_STEP_DEFAULT;
uint8_t opt_sensor_min_threshold_value_to_activate = BLUR_OPT_SENSOR_MIN_BASELINE_DEFAULT;
#else
uint8_t opt_sensor_detection_threshold_high = 128;
uint8_t opt_sensor_detection_threshold_low = 32;
uint8_t opt_sensor_min_threshold_value_to_activate = OPT_SENSOR_MIN_THRESHOLD_VALUE_TO_ACTIVATE;
#endif

uint32_t opt_sensor_block_signal_detection_delay = OPT_SENSOR_BLOCK_SIGNAL_DETECTION_DELAY;
uint8_t opt_sensor_ignore_all_duplicates = 0;
uint8_t opt_sensor_filter_mode = 0;

uint32_t opt_sensor_block_signal_detection_until = 0;
uint32_t opt_sensor_disable_debug_detection_flag_after = 0;
uint8_t opt_sensor_detected_signal_start_eye = 0;
bool opt_sensor_detected_signal_start_eye_set = false;
bool opt_sensor_initiated_sending_ir_signal = false;
volatile uint8_t opt_sensor_channel = 0;
bool opt_sensor_readings_active = false;
bool opt_sensor_reading_triggered[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_reading_triggered_count[OPT_SENSOR_CHANNELS];
bool opt_sensor_ignore_duplicate[OPT_SENSOR_CHANNELS];
bool opt_sensor_duplicate_frame[OPT_SENSOR_CHANNELS];
uint16_t opt_sensor_duplicate_frames_in_a_row_counter = 0;
uint8_t other_channel = 0;
uint8_t opt_sensor_readings_last[OPT_SENSOR_CHANNELS];

#ifdef OPT_SENSOR_FILTER_ADC_SIGNAL
uint8_t opt_sensor_readings_realtime_filter[OPT_SENSOR_CHANNELS];
#endif

uint16_t opt_sensor_reading_counter = 0;
uint16_t opt_sensor_duplicate_frames_counter = 0;
uint16_t opt_sensor_premature_frames_counter = 0;
volatile uint8_t opt_sensor_readings[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_readings_high[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_readings_low[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_readings_threshold_high[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_readings_threshold_low[OPT_SENSOR_CHANNELS];

uint16_t opt_sensor_ss_reading_counter = 0;
uint16_t opt_sensor_ss_duplicate_frames_counter = 0;
uint16_t opt_sensor_ss_premature_frames_counter = 0;
uint16_t opt_sensor_ss_channel_frequency_detection_counter[OPT_SENSOR_CHANNELS];
volatile uint8_t opt_sensor_ss_readings[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_ss_readings_high[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_ss_readings_low[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_ss_readings_threshold_high[OPT_SENSOR_CHANNELS];
uint8_t opt_sensor_ss_readings_threshold_low[OPT_SENSOR_CHANNELS];

// A0/PF7/ADC7 = right-side optical sensor, A1/PF6/ADC6 = left-side optical sensor.
const uint8_t admux[OPT_SENSOR_CHANNELS] = {ADC7D, ADC6D};

#ifdef BLUR_REDUCTION_FIRMWARE
volatile uint16_t opt_sensor_blur_detected_counter = 0;       // accepted panel refresh dips
volatile uint16_t opt_sensor_blur_rejected_counter = 0;       // lockout/full-queue/noise rejects
volatile uint16_t opt_sensor_blur_forwarded_dip_counter = 0;  // dips forwarded to IR scheduler
volatile uint16_t opt_sensor_blur_phase_rejected_counter = 0; // accepted panel dips gated by even/odd phase
volatile uint8_t opt_sensor_blur_last_detection_channel = 0;
volatile uint8_t opt_sensor_blur_pending_detection = 0;
volatile uint32_t opt_sensor_blur_pending_time_us = 0;
volatile uint16_t opt_sensor_blur_pending_timer1_tcnt = 0;
volatile uint8_t opt_sensor_blur_pending_channel = 0;
volatile uint8_t opt_sensor_blur_panel_phase = 0;
volatile uint8_t opt_sensor_blur_selected_phase = 0;
volatile uint8_t opt_sensor_blur_last_forwarded_phase = 0;

uint8_t opt_sensor_blur_required_falling_samples = BLUR_OPT_SENSOR_REQUIRED_FALLING_SAMPLES_DEFAULT;
uint8_t opt_sensor_blur_baseline_shift = BLUR_OPT_SENSOR_BASELINE_SHIFT_DEFAULT;
uint8_t opt_sensor_blur_brightness_change_threshold = BLUR_PHASE_BRIGHTNESS_CHANGE_THRESHOLD_DEFAULT;
uint8_t opt_sensor_blur_phase_score_margin = BLUR_PHASE_SCORE_MARGIN_DEFAULT;

static uint16_t opt_sensor_blur_baseline_scaled[OPT_SENSOR_CHANNELS];
static uint8_t opt_sensor_blur_initialized[OPT_SENSOR_CHANNELS];
static uint8_t opt_sensor_blur_falling_count[OPT_SENSOR_CHANNELS];
static uint16_t opt_sensor_blur_channel_detections[OPT_SENSOR_CHANNELS];
static uint16_t opt_sensor_blur_channel_rejections[OPT_SENSOR_CHANNELS];
static uint8_t opt_sensor_blur_last_sample[OPT_SENSOR_CHANNELS];
static uint16_t opt_sensor_blur_phase_score[2];
static uint16_t opt_sensor_blur_last_interval_brightness = 0;
static uint16_t opt_sensor_blur_last_brightness_change = 0;
static uint32_t opt_sensor_blur_last_panel_dip_time_us = 0;
static uint8_t opt_sensor_blur_last_panel_phase = 0;
static uint8_t opt_sensor_blur_last_interval_brightness_set = 0;
static uint8_t opt_sensor_blur_last_panel_dip_time_set = 0;
#endif

#ifdef BLUR_REDUCTION_FIRMWARE
static inline uint8_t opt_sensor_blur_phase_mode(void)
{
    uint8_t mode = opt_sensor_ignore_all_duplicates;
    if (mode > BLUR_PHASE_MODE_MANUAL_1) {
        mode = BLUR_PHASE_MODE_AUTO;
    }
    return mode;
}

static inline bool opt_sensor_blur_phase_gate_enabled(void)
{
    return opt_sensor_blur_phase_mode() != BLUR_PHASE_MODE_ALL;
}

static inline uint32_t opt_sensor_blur_expected_panel_period_us(void)
{
    if (target_frametime == 0) {
        return 0;
    }

    // In phase-gated mode target_frametime is the *video* frame period.
    // The optical panel dip cadence is expected to be twice as fast on
    // 60 Hz-in / 120 Hz-panel style sources, so use half for lockout/parity.
    if (opt_sensor_blur_phase_gate_enabled() && target_frametime > 1) {
        return ((uint32_t)target_frametime) >> 1;
    }
    return target_frametime;
}

static inline uint32_t opt_sensor_blur_lockout_us(void)
{
    uint32_t lockout = opt_sensor_block_signal_detection_delay;
    uint32_t expected_panel = opt_sensor_blur_expected_panel_period_us();

    if (expected_panel > 0) {
        if (lockout == 0) {
            lockout = expected_panel >> 1;
        }
        // Do not let the duplicate-suppression lockout hide the next panel
        // dip.  Phase detection needs to see both even and odd panel scans.
        uint32_t max_lockout = expected_panel - (expected_panel >> 3); // 87.5%
        if (max_lockout > 0 && lockout > max_lockout) {
            lockout = max_lockout;
        }
    }

    if (lockout < BLUR_OPT_SENSOR_MIN_LOCKOUT_US) {
        lockout = BLUR_OPT_SENSOR_MIN_LOCKOUT_US;
    }
    return lockout;
}

static inline uint16_t opt_sensor_blur_current_brightness(void)
{
    uint8_t shift = opt_sensor_blur_baseline_shift;
    if (shift < 1) shift = 1;
    if (shift > 7) shift = 7;

    uint16_t total = 0;
    for (uint8_t c = 0; c < OPT_SENSOR_CHANNELS; c++) {
        total += (opt_sensor_blur_baseline_scaled[c] >> shift);
    }
    return total;
}

static inline uint8_t opt_sensor_blur_auto_phase(void)
{
    uint16_t margin = opt_sensor_blur_phase_score_margin;
    if (opt_sensor_blur_phase_score[1] > (uint16_t)(opt_sensor_blur_phase_score[0] + margin)) {
        return 1;
    }
    if (opt_sensor_blur_phase_score[0] > (uint16_t)(opt_sensor_blur_phase_score[1] + margin)) {
        return 0;
    }
    return opt_sensor_blur_selected_phase;
}

static inline uint8_t opt_sensor_blur_selected_phase_now(void)
{
    uint8_t mode = opt_sensor_blur_phase_mode();
    if (mode == BLUR_PHASE_MODE_MANUAL_0) {
        return 0;
    }
    if (mode == BLUR_PHASE_MODE_MANUAL_1) {
        return 1;
    }
    return opt_sensor_blur_auto_phase();
}

static inline void opt_sensor_blur_decay_score(uint8_t phase)
{
    uint8_t shift = BLUR_PHASE_SCORE_DECAY_SHIFT;
    if (shift > 0 && opt_sensor_blur_phase_score[phase] > 0) {
        opt_sensor_blur_phase_score[phase] -= (opt_sensor_blur_phase_score[phase] >> shift);
    }
}

static inline void opt_sensor_blur_update_phase_evidence(uint8_t current_phase)
{
    uint16_t brightness = opt_sensor_blur_current_brightness();

    if (opt_sensor_blur_last_interval_brightness_set) {
        uint16_t diff = (brightness > opt_sensor_blur_last_interval_brightness)
            ? (brightness - opt_sensor_blur_last_interval_brightness)
            : (opt_sensor_blur_last_interval_brightness - brightness);
        opt_sensor_blur_last_brightness_change = diff;

        // The brightness interval we are ending began at the previous panel
        // dip.  If it differs from the interval before it, that previous dip
        // was probably the real video-frame update, not merely the duplicate
        // panel rescan.
        uint8_t previous_phase = current_phase ^ 1;
        if (diff >= opt_sensor_blur_brightness_change_threshold) {
            uint16_t inc = diff;
            if (inc > 64) inc = 64;
            uint16_t next = opt_sensor_blur_phase_score[previous_phase] + inc;
            opt_sensor_blur_phase_score[previous_phase] = (next < opt_sensor_blur_phase_score[previous_phase]) ? 0xFFFF : next;
            opt_sensor_blur_decay_score(previous_phase ^ 1);
            opt_sensor_blur_selected_phase = opt_sensor_blur_auto_phase();
        } else {
            opt_sensor_blur_decay_score(0);
            opt_sensor_blur_decay_score(1);
        }
    } else {
        opt_sensor_blur_last_interval_brightness_set = 1;
    }

    opt_sensor_blur_last_interval_brightness = brightness;
}

static inline uint8_t opt_sensor_blur_current_panel_phase(uint32_t now)
{
    uint8_t phase = opt_sensor_blur_panel_phase;
    uint32_t expected_panel = opt_sensor_blur_expected_panel_period_us();

    if (opt_sensor_blur_last_panel_dip_time_set && expected_panel > 0) {
        uint32_t dt = now - opt_sensor_blur_last_panel_dip_time_us;
        uint32_t elapsed = (dt + (expected_panel >> 1)) / expected_panel;
        if (elapsed < 1) elapsed = 1;
        phase = opt_sensor_blur_last_panel_phase ^ (elapsed & 1);
    }

    return phase & 1;
}

static inline bool opt_sensor_blur_register_panel_dip(uint32_t now, uint8_t ch)
{
    (void)ch;
    uint8_t phase = opt_sensor_blur_current_panel_phase(now);
    opt_sensor_blur_panel_phase = phase ^ 1;
    opt_sensor_blur_last_panel_phase = phase;
    opt_sensor_blur_last_panel_dip_time_us = now;
    opt_sensor_blur_last_panel_dip_time_set = 1;

    opt_sensor_blur_update_phase_evidence(phase);

    if (!opt_sensor_blur_phase_gate_enabled()) {
        opt_sensor_blur_selected_phase = phase;
        opt_sensor_blur_last_forwarded_phase = phase;
        return true;
    }

    uint8_t selected = opt_sensor_blur_selected_phase_now();
    opt_sensor_blur_selected_phase = selected;
    if (phase == selected) {
        opt_sensor_blur_last_forwarded_phase = phase;
        return true;
    }

    opt_sensor_blur_phase_rejected_counter++;
    return false;
}

void opt_sensor_blur_toggle_phase_override(void)
{
    uint8_t mode = opt_sensor_blur_phase_mode();
    uint8_t next_phase;
    if (mode == BLUR_PHASE_MODE_MANUAL_0) {
        next_phase = 1;
    } else if (mode == BLUR_PHASE_MODE_MANUAL_1) {
        next_phase = 0;
    } else {
        next_phase = opt_sensor_blur_selected_phase_now() ^ 1;
    }
    opt_sensor_ignore_all_duplicates = next_phase ? BLUR_PHASE_MODE_MANUAL_1 : BLUR_PHASE_MODE_MANUAL_0;
    opt_sensor_blur_selected_phase = next_phase;
}

static inline bool opt_sensor_time_reached(uint32_t now, uint32_t target)
{
    return ((int32_t)(now - target)) >= 0;
}

static inline void opt_sensor_blur_update_baseline(uint8_t ch, uint8_t reading)
{
    uint8_t shift = opt_sensor_blur_baseline_shift;
    if (shift < 1) shift = 1;
    if (shift > 7) shift = 7;

    if (!opt_sensor_blur_initialized[ch]) {
        opt_sensor_blur_baseline_scaled[ch] = ((uint16_t)reading) << shift;
        opt_sensor_blur_last_sample[ch] = reading;
        opt_sensor_blur_initialized[ch] = 1;
        return;
    }

    uint16_t baseline = opt_sensor_blur_baseline_scaled[ch] >> shift;
    int16_t err = (int16_t)reading - (int16_t)baseline;
    opt_sensor_blur_baseline_scaled[ch] = (uint16_t)((int16_t)opt_sensor_blur_baseline_scaled[ch] + err);
}

static inline bool opt_sensor_blur_detect_sample(uint8_t ch, uint8_t reading)
{
    uint8_t shift = opt_sensor_blur_baseline_shift;
    if (shift < 1) shift = 1;
    if (shift > 7) shift = 7;

    if (!opt_sensor_blur_initialized[ch]) {
        opt_sensor_blur_update_baseline(ch, reading);
        return false;
    }

    uint8_t last = opt_sensor_blur_last_sample[ch];
    uint16_t baseline = opt_sensor_blur_baseline_scaled[ch] >> shift;
    uint8_t dip_delta = opt_sensor_detection_threshold_high;
    uint8_t step_delta = opt_sensor_detection_threshold_low;
    if (dip_delta == 0) dip_delta = 1;
    if (step_delta == 0) step_delta = 1;

    bool baseline_ok = (opt_sensor_min_threshold_value_to_activate == 0) ||
                       (baseline >= opt_sensor_min_threshold_value_to_activate);
    bool falling = ((uint16_t)last >= (uint16_t)reading + step_delta);
    bool below_baseline = (baseline >= (uint16_t)reading + dip_delta);
    bool detected = false;

    if (baseline_ok && falling && below_baseline) {
        if (opt_sensor_blur_falling_count[ch] < 0xFF) {
            opt_sensor_blur_falling_count[ch]++;
        }
        if (opt_sensor_blur_falling_count[ch] >= opt_sensor_blur_required_falling_samples) {
            detected = true;
            opt_sensor_blur_falling_count[ch] = 0;
        }
    } else {
        if (reading >= last) {
            opt_sensor_blur_falling_count[ch] = 0;
        }
    }

    // Do not drag the baseline down while the dip is in progress.  Updating on
    // recovery lets the baseline track slow scene brightness changes without
    // eating the short OLED refresh dip we are trying to detect.
    if (!below_baseline || reading >= last) {
        opt_sensor_blur_update_baseline(ch, reading);
    }

    opt_sensor_blur_last_sample[ch] = reading;
    return detected;
}
#endif

void opt_sensor_init(void)
{
#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
    ir_led_token_active_countdown = 0;
#endif
#ifdef OPT_SENSOR_ENABLE_STATS
    opt_sensor_stats_count = 0;
#endif
    opt_sensor_block_signal_detection_until = 0;
    opt_sensor_disable_debug_detection_flag_after = 0;
    opt_sensor_detected_signal_start_eye = 0;
    opt_sensor_detected_signal_start_eye_set = false;
    opt_sensor_initiated_sending_ir_signal = false;
    opt_sensor_channel = 0;
    opt_sensor_readings_active = false;
    memset((void *)opt_sensor_reading_triggered, 0, sizeof(opt_sensor_reading_triggered));
    memset((void *)opt_sensor_reading_triggered_count, 0, sizeof(opt_sensor_reading_triggered_count));
    memset((void *)opt_sensor_ignore_duplicate, 0, sizeof(opt_sensor_ignore_duplicate));
    memset((void *)opt_sensor_duplicate_frame, 0, sizeof(opt_sensor_duplicate_frame));
    opt_sensor_duplicate_frames_in_a_row_counter = 0;
    other_channel = 0;
    opt_sensor_reading_counter = 0;
    opt_sensor_duplicate_frames_counter = 0;
    opt_sensor_premature_frames_counter = 0;
    memset((void *)opt_sensor_readings_last, 0, sizeof(opt_sensor_readings_last));
#ifdef OPT_SENSOR_FILTER_ADC_SIGNAL
    memset((void *)opt_sensor_readings_realtime_filter, 0, sizeof(opt_sensor_readings_realtime_filter));
#endif
    memset((void *)opt_sensor_readings, 0, sizeof(opt_sensor_readings));
    memset((void *)opt_sensor_readings_high, 0, sizeof(opt_sensor_readings_high));
    memset((void *)opt_sensor_readings_low, 255, sizeof(opt_sensor_readings_low));
    memset((void *)opt_sensor_readings_threshold_high, 255, sizeof(opt_sensor_readings_threshold_high));
    memset((void *)opt_sensor_readings_threshold_low, 0, sizeof(opt_sensor_readings_threshold_low));

#ifdef BLUR_REDUCTION_FIRMWARE
    opt_sensor_blur_detected_counter = 0;
    opt_sensor_blur_rejected_counter = 0;
    opt_sensor_blur_forwarded_dip_counter = 0;
    opt_sensor_blur_phase_rejected_counter = 0;
    opt_sensor_blur_last_detection_channel = 0;
    opt_sensor_blur_pending_detection = 0;
    opt_sensor_blur_pending_time_us = 0;
    opt_sensor_blur_pending_timer1_tcnt = 0;
    opt_sensor_blur_pending_channel = 0;
    opt_sensor_blur_panel_phase = 0;
    opt_sensor_blur_selected_phase = 0;
    opt_sensor_blur_last_forwarded_phase = 0;
    opt_sensor_blur_last_interval_brightness = 0;
    opt_sensor_blur_last_brightness_change = 0;
    opt_sensor_blur_last_panel_dip_time_us = 0;
    opt_sensor_blur_last_panel_phase = 0;
    opt_sensor_blur_last_interval_brightness_set = 0;
    opt_sensor_blur_last_panel_dip_time_set = 0;
    memset((void *)opt_sensor_blur_baseline_scaled, 0, sizeof(opt_sensor_blur_baseline_scaled));
    memset((void *)opt_sensor_blur_initialized, 0, sizeof(opt_sensor_blur_initialized));
    memset((void *)opt_sensor_blur_falling_count, 0, sizeof(opt_sensor_blur_falling_count));
    memset((void *)opt_sensor_blur_channel_detections, 0, sizeof(opt_sensor_blur_channel_detections));
    memset((void *)opt_sensor_blur_channel_rejections, 0, sizeof(opt_sensor_blur_channel_rejections));
    memset((void *)opt_sensor_blur_last_sample, 0, sizeof(opt_sensor_blur_last_sample));
    memset((void *)opt_sensor_blur_phase_score, 0, sizeof(opt_sensor_blur_phase_score));
    ir_signal_blur_reset();
#endif

    ADMUX = _BV(REFS0) | _BV(ADLAR) | (admux[opt_sensor_channel] & 0x07);
    ADCSRB = 0
        | _BV(ADHSM)  // high speed ADC mode on ATmega32U4
        ;
    ADCSRA = _BV(ADEN) | _BV(ADSC) | _BV(ADIF) | _BV(ADIE) | 4; // prescaler 16
}

void opt_sensor_stop(void)
{
    ADCSRA &= ~(_BV(ADEN) | _BV(ADIE));
}

#ifdef OPT_SENSOR_ENABLE_STATS
void opt_sensor_print_stats(void)
{
#ifdef BLUR_REDUCTION_FIRMWARE
    switch (opt_sensor_stats_count) {
    case 0:
        opt_sensor_ss_reading_counter = opt_sensor_reading_counter;
        opt_sensor_ss_duplicate_frames_counter = opt_sensor_blur_detected_counter;
        opt_sensor_ss_premature_frames_counter = opt_sensor_blur_rejected_counter;
        opt_sensor_ss_channel_frequency_detection_counter[0] = opt_sensor_blur_forwarded_dip_counter;
        opt_sensor_ss_channel_frequency_detection_counter[1] = opt_sensor_blur_phase_rejected_counter;
        for (int ch = 0; ch < OPT_SENSOR_CHANNELS; ch++) {
            opt_sensor_ss_readings[ch] = opt_sensor_readings[ch];
            opt_sensor_ss_readings_high[ch] = opt_sensor_readings_high[ch];
            opt_sensor_ss_readings_low[ch] = opt_sensor_readings_low[ch];
            opt_sensor_ss_readings_threshold_high[ch] = opt_sensor_blur_baseline_scaled[ch] >> opt_sensor_blur_baseline_shift;
            opt_sensor_ss_readings_threshold_low[ch] = opt_sensor_blur_channel_detections[ch];
        }
        opt_sensor_clear_stats();
        break;
    case 1 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print("+stats blur reading_counter:");
        Serial.print(opt_sensor_ss_reading_counter);
        break;
    case 2 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" panel_dips:");
        Serial.print(opt_sensor_ss_duplicate_frames_counter);
        break;
    case 3 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" rejected:");
        Serial.print(opt_sensor_ss_premature_frames_counter);
        Serial.print(" forwarded:");
        Serial.print(opt_sensor_ss_channel_frequency_detection_counter[0]);
        Serial.print(" phase_gated:");
        Serial.print(opt_sensor_ss_channel_frequency_detection_counter[1]);
        Serial.print(" phase_mode:");
        Serial.print(opt_sensor_blur_phase_mode());
        Serial.print(" selected_phase:");
        Serial.print(opt_sensor_blur_selected_phase);
        Serial.print(" score0:");
        Serial.print(opt_sensor_blur_phase_score[0]);
        Serial.print(" score1:");
        Serial.print(opt_sensor_blur_phase_score[1]);
        Serial.print(" brightness_change:");
        Serial.print(opt_sensor_blur_last_brightness_change);
        Serial.print(" dip_delta:");
        Serial.print(opt_sensor_detection_threshold_high);
        Serial.print(" step_delta:");
        Serial.print(opt_sensor_detection_threshold_low);
        Serial.println();
        opt_sensor_stats_count += OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY;
        break;
    case 5 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print("+stats blur channel:right");
        break;
    case 6 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" detections:");
        Serial.print(opt_sensor_ss_readings_threshold_low[0]);
        break;
    case 7 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" reading:");
        Serial.print(opt_sensor_ss_readings[0]);
        break;
    case 8 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" high:");
        Serial.print(opt_sensor_ss_readings_high[0]);
        break;
    case 9 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" low:");
        Serial.print(opt_sensor_ss_readings_low[0]);
        break;
    case 10 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" baseline:");
        Serial.print(opt_sensor_ss_readings_threshold_high[0]);
        Serial.println();
        opt_sensor_stats_count += 2 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY;
        break;
    case 13 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print("+stats blur channel:left");
        break;
    case 14 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" detections:");
        Serial.print(opt_sensor_ss_readings_threshold_low[1]);
        break;
    case 15 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" reading:");
        Serial.print(opt_sensor_ss_readings[1]);
        break;
    case 16 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" high:");
        Serial.print(opt_sensor_ss_readings_high[1]);
        break;
    case 17 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" low:");
        Serial.print(opt_sensor_ss_readings_low[1]);
        break;
    case 18 * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY:
        Serial.print(" baseline:");
        Serial.print(opt_sensor_ss_readings_threshold_high[1]);
        Serial.println();
        opt_sensor_stats_count += OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY;
        break;
    }
    opt_sensor_stats_count++;
#else
    // The non-blur firmware normally uses the upstream implementation.
#endif
}

bool opt_sensor_finish_print_stats(void)
{
    bool done = (opt_sensor_stats_count > (4 + 8 * 2) * OPT_SENSOR_STATS_SERIAL_OUTPUT_FREQUENCY);
    if (done) {
        opt_sensor_stats_count = 0;
    }
    return done;
}
#endif

void opt_sensor_update_thresholds(void)
{
#ifdef BLUR_REDUCTION_FIRMWARE
    opt_sensor_readings_active = true;
    for (uint8_t c = 0; c < OPT_SENSOR_CHANNELS; c++) {
        uint8_t shift = opt_sensor_blur_baseline_shift;
        if (shift < 1) shift = 1;
        if (shift > 7) shift = 7;
        uint16_t baseline = opt_sensor_blur_baseline_scaled[c] >> shift;
        if (opt_sensor_min_threshold_value_to_activate > 0 && baseline < opt_sensor_min_threshold_value_to_activate) {
            opt_sensor_readings_active = false;
        }
        opt_sensor_readings_threshold_high[c] = (uint8_t)((baseline > 255) ? 255 : baseline);
        opt_sensor_readings_threshold_low[c] = (uint8_t)((baseline > opt_sensor_detection_threshold_high) ? (baseline - opt_sensor_detection_threshold_high) : 0);
    }
#endif
}

void opt_sensor_settings_changed(void)
{
#ifdef BLUR_REDUCTION_FIRMWARE
    if (opt_sensor_blur_required_falling_samples < 1) {
        opt_sensor_blur_required_falling_samples = 1;
    }
    if (opt_sensor_blur_baseline_shift < 1) opt_sensor_blur_baseline_shift = 1;
    if (opt_sensor_blur_baseline_shift > 7) opt_sensor_blur_baseline_shift = 7;
    if (opt_sensor_ignore_all_duplicates > BLUR_PHASE_MODE_MANUAL_1) {
        opt_sensor_ignore_all_duplicates = BLUR_PHASE_MODE_AUTO;
    }
#endif
}

void opt_sensor_check_readings(void)
{
#ifdef BLUR_REDUCTION_FIRMWARE
    uint8_t checked_readings[OPT_SENSOR_CHANNELS];
    uint8_t pending = 0;
    uint32_t pending_time = 0;
    uint16_t pending_tcnt = 0;
    uint8_t pending_channel = 0;

    for (uint8_t c = 0; c < OPT_SENSOR_CHANNELS; c++) {
        checked_readings[c] = opt_sensor_readings[c];
    }

    cli();
    if (opt_sensor_blur_pending_detection) {
        pending = 1;
        pending_time = opt_sensor_blur_pending_time_us;
        pending_tcnt = opt_sensor_blur_pending_timer1_tcnt;
        pending_channel = opt_sensor_blur_pending_channel;
        opt_sensor_blur_pending_detection = 0;
    }
    sei();

    opt_sensor_current_time = pending ? pending_time : micros();

    if (pending) {
        opt_sensor_detected_signal_start_eye = pending_channel;
        opt_sensor_detected_signal_start_eye_set = true;
        opt_sensor_initiated_sending_ir_signal = true;
        opt_sensor_reading_triggered[pending_channel] = true;
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
        opt_sensor_disable_debug_detection_flag_after = opt_sensor_current_time + (opt_sensor_blur_lockout_us() >> 2);
        if (pending_channel) {
            bitSet(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
        } else {
            bitSet(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
        }
#endif
        ir_signal_process_blur_refresh(pending_time, pending_tcnt);
    }

#ifdef OPT_SENSOR_ENABLE_STREAM_READINGS_TO_SERIAL
    if (opt_sensor_enable_stream_readings_to_serial) {
        uint8_t buffer[3 + 10 + 2] = {'+', 'o', ' ', 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, '\r', '\n'};
        uint8_t ch0_trigger = opt_sensor_reading_triggered[0] ? 0x01 : 0x00;
        uint8_t ch1_trigger = opt_sensor_reading_triggered[1] ? 0x08 : 0x00;
        buffer[3] = 0x80 | ch0_trigger | ch1_trigger;
        buffer[4] = 0x80 |
                    (opt_sensor_readings_active ? 0x08 : 0x00) |
                    (opt_sensor_detected_signal_start_eye == 1 ? 0x04 : 0x00) |
                    (opt_sensor_initiated_sending_ir_signal ? 0x02 : 0x00) |
                    (opt_sensor_block_signal_detection_until > 0 ? 0x01 : 0x00);
        buffer[5] = 0x80 | (opt_sensor_blur_last_detection_channel & 0x7f);
        buffer[6] = 0x80 | ((checked_readings[0] >> 2) & 0x3f);
        buffer[7] = 0x80 | ((checked_readings[1] >> 3) & 0x1f) | ((checked_readings[0] << 5) & 0x60);
        buffer[8] = 0x80 | ((opt_sensor_current_time >> 28) & 0x0f) | ((checked_readings[1] << 4) & 0x70);
        buffer[9] = 0x80 | ((opt_sensor_current_time >> 21) & 0x7f);
        buffer[10] = 0x80 | ((opt_sensor_current_time >> 14) & 0x7f);
        buffer[11] = 0x80 | ((opt_sensor_current_time >> 7) & 0x7f);
        buffer[12] = 0x80 | ((opt_sensor_current_time >> 0) & 0x7f);
        Serial.write(buffer, 15);
        opt_sensor_initiated_sending_ir_signal = false;
        opt_sensor_reading_triggered[0] = false;
        opt_sensor_reading_triggered[1] = false;
    }
#endif

    for (uint8_t c = 0; c < OPT_SENSOR_CHANNELS; c++) {
        uint8_t reading = checked_readings[c];
        opt_sensor_readings_last[c] = reading;
        opt_sensor_reading_counter++;
        if (reading > opt_sensor_readings_high[c]) opt_sensor_readings_high[c] = reading;
        if (reading < opt_sensor_readings_low[c]) opt_sensor_readings_low[c] = reading;
    }

#ifdef ENABLE_DEBUG_PIN_OUTPUTS
    if (opt_sensor_disable_debug_detection_flag_after) {
        if (opt_sensor_time_reached(micros(), opt_sensor_disable_debug_detection_flag_after)) {
            opt_sensor_disable_debug_detection_flag_after = 0;
            bitClear(PORT_DEBUG_DETECTED_RIGHT_D5, DEBUG_DETECTED_RIGHT_D5);
            bitClear(PORT_DEBUG_DETECTED_LEFT_D4, DEBUG_DETECTED_LEFT_D4);
        }
    }
#endif

#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
    if (opt_sensor_enable_ignore_during_ir == 1) {
        cli();
        if (ir_led_token_active_flag) {
            ir_led_token_active_countdown = 10;
            if (!ir_led_token_active) {
                ir_led_token_active_flag = false;
            }
        }
        sei();
        if (ir_led_token_active_countdown > 0) {
            ir_led_token_active_countdown -= 1;
        }
    }
#endif
#endif
}

void opt_sensor_clear_stats(void)
{
    opt_sensor_reading_counter = 0;
    opt_sensor_duplicate_frames_counter = 0;
    opt_sensor_premature_frames_counter = 0;
    memset((void *)opt_sensor_readings_high, 0, sizeof(opt_sensor_readings_high));
    memset((void *)opt_sensor_readings_low, 255, sizeof(opt_sensor_readings_low));
#ifdef BLUR_REDUCTION_FIRMWARE
    opt_sensor_blur_detected_counter = 0;
    opt_sensor_blur_rejected_counter = 0;
    opt_sensor_blur_forwarded_dip_counter = 0;
    opt_sensor_blur_phase_rejected_counter = 0;
    memset((void *)opt_sensor_blur_channel_detections, 0, sizeof(opt_sensor_blur_channel_detections));
    memset((void *)opt_sensor_blur_channel_rejections, 0, sizeof(opt_sensor_blur_channel_rejections));
#endif
}

void opt_sensor_adc_isr_handler(void)
{
    uint8_t reading = ADCH;
    uint8_t ch = opt_sensor_channel;

#ifdef OPT_SENSOR_FILTER_ADC_SIGNAL
    if (opt_sensor_filter_mode == 1) {
        uint8_t filter = opt_sensor_readings_realtime_filter[ch];
        uint8_t reading_last = opt_sensor_readings[ch];
        if ((reading > filter && filter > reading_last) || (reading < filter && filter < reading_last)) {
            opt_sensor_readings[ch] = filter;
        } else {
            opt_sensor_readings[ch] = reading;
        }
        opt_sensor_readings_realtime_filter[ch] = reading;
    } else {
        opt_sensor_readings[ch] = reading;
    }
#else
    opt_sensor_readings[ch] = reading;
#endif

#ifdef BLUR_REDUCTION_FIRMWARE
#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
    bool ignore_for_ir = (opt_sensor_enable_ignore_during_ir == 1) && (ir_led_token_active || ir_led_token_active_countdown > 0);
#else
    bool ignore_for_ir = false;
#endif
    if (!ignore_for_ir && opt_sensor_blur_detect_sample(ch, opt_sensor_readings[ch])) {
        uint32_t now = micros();
        if (opt_sensor_block_signal_detection_until == 0 || opt_sensor_time_reached(now, opt_sensor_block_signal_detection_until)) {
            bool forward_to_ir = opt_sensor_blur_register_panel_dip(now, ch);
            opt_sensor_block_signal_detection_until = now + opt_sensor_blur_lockout_us();
            opt_sensor_blur_detected_counter++;
            opt_sensor_blur_channel_detections[ch]++;
            opt_sensor_blur_last_detection_channel = ch;

            if (forward_to_ir && !opt_sensor_blur_pending_detection) {
                opt_sensor_blur_pending_time_us = now;
                opt_sensor_blur_pending_timer1_tcnt = TCNT1;
                opt_sensor_blur_pending_channel = ch;
                opt_sensor_blur_pending_detection = 1;
                opt_sensor_blur_forwarded_dip_counter++;
            } else if (forward_to_ir) {
                opt_sensor_blur_rejected_counter++;
                opt_sensor_blur_channel_rejections[ch]++;
            }
        } else {
            opt_sensor_blur_rejected_counter++;
            opt_sensor_blur_channel_rejections[ch]++;
        }
    }
#endif

    opt_sensor_channel++;
    if (opt_sensor_channel >= OPT_SENSOR_CHANNELS) {
        opt_sensor_channel = 0;
    }
    ADMUX = (ADMUX & 0xf8) | (admux[opt_sensor_channel] & 0x07);
    bitSet(ADCSRA, ADSC);
}
