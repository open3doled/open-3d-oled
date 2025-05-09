/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */

#ifndef _IR_GLASSES_H_
#define _IR_GLASSES_H_

// TV Details
// https://forums.blurbusters.com/viewtopic.php?f=7&t=4605&sid=9d9e7ad4dc9811c700236a783fad8fdc
// https://theappliancesreviews.com/va-vs-ips-vs-ads-panel-in-tvs-review/
// Token patterns from this paper, but corrected, 2012-28-woods-helliwell-cross-compatibility_of_shutter_glasses.pdf

#define MAX_IR_SIGNAL_TIMINGS 15
#define NUM_IR_SIGNAL_TYPES 12

typedef struct
{
    uint16_t mode;         // shutter glasses toggle at (0 - start of token, 1 - end of end token) // not sure why this needed to be uint16_t but uint8_t broke the timing pulses perhaps it needs to be 16bit word aligned
    uint16_t token_length; // to align end of start tokens
    uint16_t size;         // also making this uint16_t incase timings needs to be 16 bit word aligned...
    uint16_t timings[MAX_IR_SIGNAL_TIMINGS];
} ir_signal_t;

typedef struct
{
    uint8_t signal_count;
    /*
      Valid Signal Indices:
        0: [DUMMY]
        1: [SIGNAL_OPEN_RIGHT]
        2: [SIGNAL_CLOSE_RIGHT]
        3: [SIGNAL_OPEN_LEFT]
        4: [SIGNAL_CLOSE_LEFT]
        3: [SIGNAL_OPEN_LEFT]
        4: [SIGNAL_CLOSE_LEFT]
        5: [SIGNAL_OPEN_RIGHT_FAST_SWAP]
        6: [SIGNAL_OPEN_LEFT_FAST_SWAP]
        7: [SIGNAL_MODE_RIGHT_AND_LEFT]
        8: [SIGNAL_MODE_RIGHT_ONLY]
        9: [SIGNAL_MODE_LEFT_ONLY]
        10: [SIGNAL_OPEN_RIGHT_CLOSE_LEFT]
        11: [SIGNAL_OPEN_LEFT_CLOSE_RIGHT]
    */
    uint8_t signal_index[NUM_IR_SIGNAL_TYPES];
    ir_signal_t signals[];
} ir_glasses_signal_library_t;

const ir_glasses_signal_library_t ir_glasses_samsung07 = {
    .signal_count = 1,
    /*
    // Needed to hard code this below due to compiler limitation.
    .signal_index = {
      [SIGNAL_OPEN_RIGHT_CLOSE_LEFT] = 0,
      // You can skip the entries for signals that are not present in the library
    },
    //*/
    .signal_index = {255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 0, 255},
    .signals = {
        // open_right_close_left_signal
        {
            .mode = 0, // haven't measured to check (there's only one token so it doesn't matter)
            .token_length = 66,
            .size = 5,
            .timings = {14, 12, 14, 12, 14}}}};

const ir_glasses_signal_library_t ir_glasses_xpand = {
    .signal_count = 2,
    /*
    // Needed to hard code this below due to compiler limitation.
    .signal_index = {
      [SIGNAL_OPEN_RIGHT_CLOSE_LEFT] = 0,
      [SIGNAL_OPEN_LEFT_CLOSE_RIGHT] = 1,
      // You can skip the entries for signals that are not present in the library
    },
    //*/
    .signal_index = {255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 0, 1},
    .signals = {
        // open_right_close_left_signal
        {
            .mode = 0, // haven't measured to check (token lengths are roughly the same though so it shouldn't matter)
            .token_length = 94,
            .size = 5,
            .timings = {18, 20, 18, 20, 18}},
        // open_left_close_right_signal
        {
            .mode = 0,
            .token_length = 96,
            .size = 3,
            .timings = {18, 60, 18}}}};

// 3DVision glasses appear to transition LCD shutter glasses N uS after the end of each token pattern. (on transition is slower than off transition)
// 3DVision glasses have a -45 degree front polarizing element and a 45 degree back polarizing element so they will work with vertical or horizontal polarized displays but with half brightness.
const ir_glasses_signal_library_t ir_glasses_3dvision = {
    .signal_count = 4,
    /*
    // Needed to hard code this below due to compiler limitation.
    .signal_index = {
      [SIGNAL_OPEN_RIGHT] = 0,
      [SIGNAL_CLOSE_RIGHT] = 1,
      [SIGNAL_OPEN_LEFT] = 2,
      [SIGNAL_CLOSE_LEFT] = 3,
      // You can skip the entries for signals that are not present in the library
    },
    //*/
    .signal_index = {255, 0, 1, 2, 3, 255, 255, 255, 255, 255, 255, 255},
    .signals = {
        // open_right_signal
        {
            .mode = 1, // measured and checked
            .token_length = 100,
            .size = 3,
            .timings = {23, 46, 31}},
        // close_right_signal
        {
            .mode = 1,
            .token_length = 141,
            .size = 3,
            .timings = {23, 78, 40}},
        // open_left_signal
        {
            .mode = 1,
            .token_length = 43,
            .size = 1,
            .timings = {43}},
        // close_left_signal
        {
            .mode = 1,
            .token_length = 68,
            .size = 3,
            .timings = {23, 21, 24}}}};

const ir_glasses_signal_library_t ir_glasses_sharp = {
    .signal_count = 2,
    /*
    // Needed to hard code this below due to compiler limitation.
    .signal_index = {
      [SIGNAL_OPEN_RIGHT_CLOSE_LEFT] = 0,
      [SIGNAL_OPEN_LEFT_CLOSE_RIGHT] = 1,
      // You can skip the entries for signals that are not present in the library
    },
    //*/
    .signal_index = {255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 0, 1},
    .signals = {
        // open_right_close_left_signal
        {
            .mode = 0, // haven't measured to check
            .token_length = 540,
            .size = 15,
            .timings = {20, 20, 20, 20, 20, 80, 20, 140, 20, 20, 20, 80, 20, 20, 20}},
        // open_left_close_right_signal
        {
            .mode = 0,
            .token_length = 440,
            .size = 15,
            .timings = {20, 20, 20, 20, 20, 60, 20, 60, 20, 20, 20, 80, 20, 20, 20}}}};

// Sony glasses appear to transition LCD shutter glasses 1000 uS after the start of each token pattern.
// Sony glasses have no front polarizing element and a horizontal back polarizing element, so they require the TV to have a vertical polarization
const ir_glasses_signal_library_t ir_glasses_sony = {
    .signal_count = 4,
    /*
    // Needed to hard code this below due to compiler limitation.
    .signal_index = {
      [SIGNAL_OPEN_RIGHT] = 0,
      [SIGNAL_CLOSE_RIGHT] = 1,
      [SIGNAL_OPEN_LEFT] = 2,
      [SIGNAL_CLOSE_LEFT] = 3,
      // You can skip the entries for signals that are not present in the library
    },
    //*/
    .signal_index = {255, 0, 1, 2, 3, 255, 255, 255, 255, 255, 255, 255},
    .signals = {
        // open_right_signal
        {
            .mode = 0, // measured to check
            .token_length = 540,
            .size = 9,
            .timings = {20, 20, 20, 20, 20, 380, 20, 20, 20}},
        // close_right_signal
        {
            .mode = 0,
            .token_length = 460,
            .size = 9,
            .timings = {20, 20, 20, 20, 20, 300, 20, 20, 20}},
        // open_left_signal
        {
            .mode = 0,
            .token_length = 380,
            .size = 9,
            .timings = {20, 20, 20, 20, 20, 220, 20, 20, 20}},
        // close_left_signal
        {
            .mode = 0,
            .token_length = 300,
            .size = 9,
            .timings = {20, 20, 20, 20, 20, 140, 20, 20, 20}}}};

// Panasonic glasses have a vertical front polarizing element and a horizontal back polarizing element, so OLED is fine but 45 degree polarized monitors will have half brightness and horizontal polarized displays will not work
const ir_glasses_signal_library_t ir_glasses_panasonic = {
    .signal_count = 9,
    /*
    // Needed to hard code this below due to compiler limitation.
    .signal_index = {
      [SIGNAL_OPEN_RIGHT] = 0,
      [SIGNAL_CLOSE_RIGHT] = 1,
      [SIGNAL_OPEN_LEFT] = 2,
      [SIGNAL_CLOSE_LEFT] = 3,
      // You can skip the entries for signals that are not present in the library
    },
    //*/
    // was 0, 1, 2, 3
    // no go tests
    // 3, 1, 2, 0 (staggered overlapping)
    // 3, 2, 1, 0 (inverted duty cycle dark vs light)
    // 3, 0, 1, 2 (left 90% dark right 90% dark)
    // 3, 1, 0, 2 (left 90% dark right 90% light)
    .signal_index = {255, 0, 1, 2, 3, 255, 255, 255, 255, 255, 255, 255},
    .signals = {
        // open_right_signal
        {
            .mode = 0, // token lengths are the same so it doesn't matter
            .token_length = 220,
            .size = 7,
            .timings = {20, 20, 20, 60, 20, 60, 20}},
        // close_right_signal
        {
            .mode = 0,
            .token_length = 220,
            .size = 7,
            .timings = {20, 60, 20, 60, 20, 20, 20}},
        // open_left_signal
        {
            .mode = 0,
            .token_length = 220,
            .size = 7,
            .timings = {20, 60, 20, 20, 20, 60, 20}},
        // close_left_signal
        {
            .mode = 0,
            .token_length = 220,
            .size = 7,
            .timings = {20, 20, 20, 100, 20, 20, 20}}}};

// Panasonic glasses have a vertical front polarizing element and a horizontal back polarizing element, so OLED is fine but 45 degree polarized monitors will have half brightness and horizontal polarized displays will not work
const ir_glasses_signal_library_t ir_glasses_panasonic_custom = {
    .signal_count = 9,
    /*
    // Needed to hard code this below due to compiler limitation.
    .signal_index = {
      [SIGNAL_OPEN_RIGHT] = 0,
      [SIGNAL_CLOSE_RIGHT] = 1,
      [SIGNAL_OPEN_LEFT] = 2,
      [SIGNAL_CLOSE_LEFT] = 3,
      [SIGNAL_OPEN_RIGHT_FAST_SWAP] = 4,
      [SIGNAL_OPEN_LEFT_FAST_SWAP] = 5,
      [SIGNAL_MODE_RIGHT_AND_LEFT] = 6,
      [SIGNAL_MODE_RIGHT_ONLY] = 7,
      [SIGNAL_MODE_LEFT_ONLY] = 8,
      // You can skip the entries for signals that are not present in the library
    },
    //*/
    .signal_index = {255, 0, 1, 2, 3, 4, 5, 6, 7, 8, 255, 255},
    .signals = {
        // open_right_signal
        {
            .mode = 0, // token lengths are the same so it doesn't matter
            .token_length = 220,
            .size = 7,
            .timings = {20, 20, 20, 60, 20, 60, 20}},
        // close_right_signal
        {
            .mode = 0,
            .token_length = 220,
            .size = 7,
            .timings = {20, 60, 20, 60, 20, 20, 20}},
        // open_left_signal
        {
            .mode = 0,
            .token_length = 220,
            .size = 7,
            .timings = {20, 60, 20, 20, 20, 60, 20}},
        // close_left_signal
        {
            .mode = 0,
            .token_length = 220,
            .size = 7,
            .timings = {20, 20, 20, 100, 20, 20, 20}},
        // open_right_fast_swap_signal
        {
            .mode = 0,
            .token_length = 220,
            .size = 7,
            .timings = {20, 100, 20, 20, 20, 20, 20}},
        // open_left_fast_swap_signal
        {
            .mode = 0,
            .token_length = 260,
            .size = 7,
            .timings = {20, 100, 20, 60, 20, 20, 20}},
        // mode_right_and_left_signal
        {
            .mode = 0,
            .token_length = 400,
            .size = 7,
            .timings = {20, 200, 20, 100, 20, 200, 20}},
        // mode_right_only_signal
        {
            .mode = 0,
            .token_length = 360,
            .size = 7,
            .timings = {20, 200, 20, 60, 20, 200, 20}},
        // mode_left_only_signal
        {
            .mode = 0,
            .token_length = 320,
            .size = 7,
            .timings = {20, 200, 20, 20, 20, 200, 20}}}};

// JX-30 DLP-Link glasses (measured from DLP projector 20 us pulses with delta T of 130 us, but the acceptable ranges with JX-30 glasses were 20 us <= pulses <= 300 us and 60 us <= delta T < 190 us)
const ir_glasses_signal_library_t ir_glasses_dlp_link = {
    .signal_count = 2,
    /*
    // Needed to hard code this below due to compiler limitation.
    .signal_index = {
      [SIGNAL_OPEN_RIGHT_CLOSE_LEFT] = 0,
      [SIGNAL_OPEN_LEFT_CLOSE_RIGHT] = 1,
      // You can skip the entries for signals that are not present in the library
    },
    //*/
    .signal_index = {255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 0, 1},
    .signals = {
        // open_right_close_left_signal
        {
            .mode = 0, // haven't measured to check
            .token_length = 20,
            .size = 1,
            .timings = {20}},
        // open_left_close_right_signal
        {
            .mode = 0, // haven't measured to check
            .token_length = 205,
            .size = 3,
            .timings = {0, 125, 20}}}}; // measured as 125 delay and 20 duration but for whatever reason it's making it too short due to processing interrupt timers so I'm just setting to 30.

const ir_glasses_signal_library_t *ir_glasses_available[] = {
    &ir_glasses_samsung07,
    &ir_glasses_xpand,
    &ir_glasses_3dvision,
    &ir_glasses_sharp,
    &ir_glasses_sony,
    &ir_glasses_panasonic,
    &ir_glasses_panasonic_custom,
    &ir_glasses_dlp_link,
};

#endif /* _IR_GLASSES_H_ */