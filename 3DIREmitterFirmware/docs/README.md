# Open3DOLED Blur Reduction Firmware Notes

This branch is for experimental optical synchronization against OLED panel
refresh artifacts. The target display behavior is not fully stable across
inputs and TV modes, so the design keeps the timing model configurable and
keeps the ADC path small.

## Goal

The firmware watches for short negative-going optical dips caused by OLED panel
scanout. Those dips are used as timing observations. The shutter glasses should
not be driven directly from every detected dip when the panel scan rate differs
from the source frame rate.

For example, a 60 Hz HDMI source on a 165 Hz panel can produce a repeating
physical cadence close to:

```text
3, 3, 3, 2 panel scans per source frame
```

If those physical events directly triggered IR output, the glasses would see a
cyclically uneven pulse train. The blur-reduction scheduler therefore separates
optical detection from IR timing.

## Timing Model

The firmware tracks two periods:

```text
target_frametime          source/IR frame period in microseconds
ir_blur_panel_period_us   physical panel scan period in microseconds
```

Common panel-period values:

```text
165 Hz -> 6061 us
120 Hz -> 8333 us
 60 Hz -> 16667 us
```

The panel period is explicitly configurable because the TV may use different
scanout rates in different modes. For example, it may scan at 165 Hz for a
60 Hz low-latency path but scan at 120 Hz for a 120 Hz input.

## Scheduler Philosophy

The ADC ISR only detects and queues panel dips. The main loop consumes the
pending observation and updates blur timing state. Timer1 compare channels B
and C still schedule the actual IR open/close events, so this design does not
consume another hardware timer.

In synthetic cadence mode:

1. Detected panel dips discipline the optical cadence tracker.
2. A small integer accumulator maps panel scans onto source-frame boundaries.
3. IR output is scheduled from a stable synthetic source-rate clock.
4. Inferred source-boundary phase applies only a slow correction to that
   synthetic clock.

This intentionally prioritizes stable glasses timing over exact replication of
the panel's uneven physical source-frame cadence.

## Cadence Modes

`ir_blur_cadence_mode` selects the scheduler behavior:

```text
0 direct      legacy behavior; detected optical events schedule IR directly
1 synthetic   stable source-rate IR clock disciplined by panel dips
```

Synthetic mode is the expected mode for 165 Hz panel scanout with 60 Hz or
30 Hz source content.

## Current Serial Parameters

The blur branch appends these fields to the existing parameter list:

```text
18 ir_blur_panel_period_us
19 ir_blur_cadence_mode
20 ir_blur_sync_correction_shift
```

`ir_blur_sync_correction_shift` controls how aggressively inferred
source-boundary timing corrects the synthetic clock. Larger values correct more
slowly.

The 3DPlayer Python client should not be expanded for this branch. A small
standalone one-off Python GUI should be created for reading and writing these
firmware parameters so the blur-reduction test workflow stays isolated.

## Known Limits

The firmware does not try to store long exact repeat sequences such as a
164.5 Hz to 60 Hz mapping. Long exact cycles are not useful on this MCU and may
imply more precision than the display actually provides. The current approach
uses a bounded integer accumulator instead.

The current synthetic mode assumes the configured panel period and source
period describe the display cadence well enough to infer source boundaries.
Manual adjustment of `ir_frame_delay`, `target_frametime`, and
`ir_blur_panel_period_us` should remain part of the test workflow.

The safe visible shutter window still has to be validated on physical hardware.
If the top or bottom of the image leaks adjacent-frame data, reduce
`ir_frame_duration` or adjust `ir_frame_delay`.

## Test Procedure

1. Set `target_frametime` to the desired glasses/source period.
2. Set `ir_blur_panel_period_us` to the measured panel scanout period.
3. Use synthetic cadence mode.
4. Enable stats and confirm panel dips are detected near the expected panel
   rate.
5. Tune `ir_frame_delay` and `ir_frame_duration` against real shutter crosstalk.
6. Store the working configuration to EEPROM only after the physical test looks
   stable.
