/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */

#include <Arduino.h>

#include "settings.h"
#include "ir_signal.h"
#include "ir_glasses.h"

// #define DEBUG_AVERAGE_TIMING_MODE

volatile uint8_t ir_drive_mode = IR_DRIVE_MODE_OPTICAL;
volatile uint8_t ir_glasses_selected = 6;
volatile uint16_t ir_frame_duration = IR_FRAME_DURATION;
volatile uint16_t ir_frame_delay = IR_FRAME_DELAY;
volatile uint16_t ir_signal_spacing = IR_SIGNAL_SPACING;
volatile uint8_t ir_average_timing_mode = 0;
volatile uint8_t ir_flip_eyes = 0;
#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
volatile bool ir_led_token_active = false;
#endif
uint16_t target_frametime = 0;

const ir_glasses_signal_library_t *volatile ir_glasses_selected_library;
const ir_glasses_signal_library_t *volatile ir_glasses_selected_library_sub_ir_signal_schedule_send_request;
const ir_glasses_signal_library_t *volatile ir_glasses_selected_library_sub_ir_signal_send;

// For timer 4
volatile ir_signal_type ir_signal_send_circular_queue[SIGNAL_SEND_QUEUE_SIZE];
volatile uint8_t ir_signal_send_circular_queue_position = 0;
volatile uint8_t ir_signal_send_circular_queue_end = 0;
volatile bool ir_signal_send_in_progress = false;
ir_signal_type ir_signal_send_current_signal = SIGNAL_NONE;
const ir_signal_t *ir_signal_send_current_definition;
const uint16_t *ir_signal_send_current_timings;
uint8_t ir_signal_send_current_token_position;
uint8_t ir_signal_send_current_token_length;
uint16_t ir_signal_send_current_token_timing;
// uint16_t ir_signal_send_last_open_right_tcnt1;
// uint16_t ir_signal_send_last_open_left_tcnt1;

// For timer 1 and isrs
ir_signal_type ir_signal_next_timer1_compb_scheduled_signal = SIGNAL_NONE;
ir_signal_type ir_signal_next_timer1_compb_start_signal = SIGNAL_NONE;
uint16_t ir_signal_next_timer1_compb_start_time = 0;
ir_signal_type ir_signal_next_timer1_compc_scheduled_signal = SIGNAL_NONE;
ir_signal_type ir_signal_next_timer1_compc_start_signal = SIGNAL_NONE;
uint16_t ir_signal_next_timer1_compc_start_time = 0;
uint16_t ir_average_timing_mode_no_trigger_counter = 0;
volatile bool ir_average_timing_mode_running[2] = {false}; // 0 - left, 1 - right
volatile bool ir_average_timing_mode_stop[2] = {false};    // 0 - left, 1 - right
volatile uint16_t ir_average_timing_mode_last_open_timer1_tcnt[2] = {0};
volatile bool ir_average_timing_mode_last_open_timer1_tcnt_set[2] = {false};

#define FRAME_HISTORY_SIZE 64
#define FRAME_HISTORY_SHIFT 6 // Log2(FRAME_HISTORY_SIZE) for efficient division

// For timer 1 isrs and ir_signal_process_trigger
uint32_t ir_signal_trigger_current_time = 0;
uint32_t ir_signal_trigger_last_time = 0;
uint16_t ir_signal_trigger_current_timer1_tcnt = 0;
uint16_t ir_signal_trigger_last_timer1_tcnt = 0;
bool ir_signal_trigger_last_time_set = false;
bool ir_signal_trigger_frametime_average_set = false;
uint32_t ir_signal_trigger_frametime_average_shifted = 0;
volatile uint16_t ir_signal_trigger_frametime_average = 0;
volatile uint16_t ir_signal_trigger_frametime_average_effective = 0;
volatile uint16_t ir_signal_trigger_frametime_average_effective_counter = 0;
volatile int16_t ir_signal_trigger_frame_delay_adjustment[2] = {0};
#ifdef DEBUG_AVERAGE_TIMING_MODE
volatile uint16_t ir_signal_trigger_logger_counter = 0;
#endif

// This should initialize timer1 for sending ir signals and timer4 for scheduling
// ir signals on both left and right eyes using two different comparators.
void ir_signal_init()
{
  cli();
  ir_drive_mode = IR_DRIVE_MODE_OPTICAL;
  ir_glasses_selected = 6;
  ir_frame_duration = IR_FRAME_DURATION;
  ir_frame_delay = IR_FRAME_DELAY;
  ir_signal_spacing = IR_SIGNAL_SPACING;
  ir_flip_eyes = 0;
#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
  ir_led_token_active = false;
#endif
  target_frametime = 0;

  for (uint8_t i = 0; i < SIGNAL_SEND_QUEUE_SIZE; i++)
  {
    ir_signal_send_circular_queue[i] = SIGNAL_NONE;
  }
  ir_signal_send_circular_queue_position = 0;
  ir_signal_send_circular_queue_end = 0;
  ir_signal_send_in_progress = false;
  ir_signal_send_current_signal = SIGNAL_NONE;

  ir_signal_next_timer1_compb_scheduled_signal = SIGNAL_NONE;
  ir_signal_next_timer1_compb_start_signal = SIGNAL_NONE;
  ir_signal_next_timer1_compb_start_time = 0;
  ir_signal_next_timer1_compc_scheduled_signal = SIGNAL_NONE;
  ir_signal_next_timer1_compc_start_signal = SIGNAL_NONE;
  ir_signal_next_timer1_compc_start_time = 0;
  ir_average_timing_mode_no_trigger_counter = 0;
  memset((void *)ir_average_timing_mode_running, 0, sizeof(ir_average_timing_mode_running));
  memset((void *)ir_average_timing_mode_stop, 0, sizeof(ir_average_timing_mode_stop));
  memset((void *)ir_average_timing_mode_last_open_timer1_tcnt, 0, sizeof(ir_average_timing_mode_last_open_timer1_tcnt));
  memset((void *)ir_average_timing_mode_last_open_timer1_tcnt_set, 0, sizeof(ir_average_timing_mode_last_open_timer1_tcnt_set));

  ir_signal_trigger_current_time = 0;
  ir_signal_trigger_last_time = 0;
  ir_signal_trigger_current_timer1_tcnt = 0;
  ir_signal_trigger_last_timer1_tcnt = 0;
  ir_signal_trigger_last_time_set = false;
  ir_signal_trigger_frametime_average_set = false;
  ir_signal_trigger_frametime_average_shifted = 0;
  ir_signal_trigger_frametime_average = 0;
  ir_signal_trigger_frametime_average_effective = 0;
  ir_signal_trigger_frametime_average_effective_counter = 0;
  memset((void *)ir_signal_trigger_frame_delay_adjustment, 0, sizeof(ir_signal_trigger_frame_delay_adjustment));

#ifdef DEBUG_AVERAGE_TIMING_MODE
  ir_signal_trigger_logger_counter = 0;
#endif
  sei();

  // Initialize timer1 for scheduling IR signal sends
  TCCR1C = 0; // Timer stopped, normal mode
  TCCR1B = 0;
  TCCR1A = 0;
  TIMSK1 = 0; // All interrupts disabled
  // bitSet(TIMSK1, TOIE1); // Enable TCNT1 overflow interrupt
  TIFR1 = 0xFF; // Clear pending interrupt flags if any
  cli();
  TCNT1 = 0;
  TCCR1B = _BV(CS11); // prescaler 8x
  sei();

  // Initialize timer4 for sending IR signal timings.
  TCCR4A = 0; // Timer stopped, normal mode
  TCCR4B = 0;
  TCCR4C = 0;
  TCCR4D = 0;
  TIMSK4 = 0; // All interrupts disabled
  // bitSet(TIMSK4, TOIE4); // Enable TCNT4 overflow interrupt
  TIFR4 = 0xFF; // Clear pending interrupt flags if any
}

/*
 This should take a specific signal and start the ir transmission immediately
 It should be called from two places.
 1) from ir_signal_process_opt_sensor when we detect a duplicate frame to send a fast switch signal.
 2) from the comparator isr used by ir_signal_schedule_send
*/
void ir_signal_send(ir_signal_type signal)
{
  uint8_t signal_index;
  ir_glasses_selected_library_sub_ir_signal_send = ir_glasses_selected_library_sub_ir_signal_schedule_send_request;
  signal_index = ir_glasses_selected_library_sub_ir_signal_send->signal_index[signal];
  if (signal_index != 255 && signal_index < ir_glasses_selected_library_sub_ir_signal_send->signal_count)
  {
    ir_signal_send_current_signal = signal;
    ir_signal_send_current_definition = &(ir_glasses_selected_library_sub_ir_signal_send->signals[signal_index]);
    ir_signal_send_current_timings = ir_signal_send_current_definition->timings;
    ir_signal_send_current_token_position = 1;
    ir_signal_send_current_token_length = ir_signal_send_current_definition->size;
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
    if (signal == SIGNAL_OPEN_LEFT || signal == SIGNAL_OPEN_LEFT_CLOSE_RIGHT || signal == SIGNAL_OPEN_LEFT_FAST_SWAP)
    {
      bitSet(PORT_DEBUG_ACTIVATE_LEFT_D7, DEBUG_ACTIVATE_LEFT_D7);
    }
    else if (signal == SIGNAL_OPEN_RIGHT_CLOSE_LEFT || signal == SIGNAL_CLOSE_LEFT)
    {
      bitClear(PORT_DEBUG_ACTIVATE_LEFT_D7, DEBUG_ACTIVATE_LEFT_D7);
      // bitClear(PORT_DEBUG_PORT_D15, DEBUG_PORT_D15);
    }
    if (signal == SIGNAL_OPEN_RIGHT || signal == SIGNAL_OPEN_RIGHT_CLOSE_LEFT || signal == SIGNAL_OPEN_RIGHT_FAST_SWAP)
    {
      bitSet(PORT_DEBUG_ACTIVATE_RIGHT_D8, DEBUG_ACTIVATE_RIGHT_D8);
    }
    else if (signal == SIGNAL_OPEN_LEFT_CLOSE_RIGHT || signal == SIGNAL_CLOSE_RIGHT)
    {
      bitClear(PORT_DEBUG_ACTIVATE_RIGHT_D8, DEBUG_ACTIVATE_RIGHT_D8);
      // bitClear(PORT_DEBUG_PORT_D15, DEBUG_PORT_D15);
    }
    if (signal == SIGNAL_OPEN_LEFT_FAST_SWAP || signal == SIGNAL_OPEN_RIGHT_FAST_SWAP)
    {
      // bitSet(PORT_DEBUG_PORT_D15, DEBUG_PORT_D15);
    }
#endif
#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
    ir_led_token_active = true;
#ifdef ENABLE_DEBUG_PIN_OUTPUTS
#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR_DEBUG_PIN_D2
    bitSet(PORT_DEBUG_PORT_D2, DEBUG_PORT_D2); // IR LED token started
#endif
#endif
#endif
    cli();
    TC4H = 0;
    TCNT4 = 0;
    TC4H = 0x03; // set timer4 top value to 1023
    OCR4C = 0xFF;
    ir_signal_send_current_token_timing = ir_signal_send_current_timings[0];
    if (ir_signal_send_current_token_timing > 0)
    {
      TC4H = (ir_signal_send_current_token_timing >> 8) & 0xFF; // High byte of 10-bit value
      OCR4A = ir_signal_send_current_token_timing & 0xFF;       // Low byte of 10-bit value
      bitSet(TIMSK4, OCIE4A);                                   // Enable IR pulse falling edge interrupt
      bitSet(PORT_LED_IR_D3, LED_IR_D3);
    }
    else
    {
      if (ir_signal_send_current_token_position < ir_signal_send_current_token_length)
      {
        ir_signal_send_current_token_timing += ir_signal_send_current_timings[ir_signal_send_current_token_position++];
        TC4H = (ir_signal_send_current_token_timing >> 8) & 0xFF; // High byte of 10-bit value
        OCR4B = ir_signal_send_current_token_timing & 0xFF;       // Low byte of 10-bit value
        bitSet(TIMSK4, OCIE4B);                                   // Enable rising edge interrupt
      }
      else
      {
        ir_signal_send_current_token_timing += ir_signal_spacing;
        TC4H = (ir_signal_send_current_token_timing >> 8) & 0xFF; // High byte of 10-bit value
        OCR4D = ir_signal_send_current_token_timing & 0xFF;       // Low byte of 10-bit value
        bitSet(TIMSK4, OCIE4D);                                   // Enable signal spacing period interrupt
#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
        ir_led_token_active = false;
// #ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR_DEBUG_PIN_D2
// bitClear(PORT_DEBUG_PORT_D2, DEBUG_PORT_D2); // IR LED token ended
// #endif
#endif
      }
    }
    TIFR4 = 0xFF;                   // Clear pending interrupts if any
    TCCR4B = _BV(CS42) | _BV(CS40); // prescaler 16x
    // TCCR4B = _BV(CS42); // prescaler 8x
    sei();
  }
  else
  {
    // The selected glasses don't support the requested signal.
    ir_signal_send_finished();
    return;
  }
}

ISR(TIMER4_COMPA_vect) // IR pulse falling edge
{
  bitClear(PORT_LED_IR_D3, LED_IR_D3);
  if (ir_signal_send_current_token_position < ir_signal_send_current_token_length)
  {
    ir_signal_send_current_token_timing += ir_signal_send_current_timings[ir_signal_send_current_token_position++];
    TC4H = (ir_signal_send_current_token_timing >> 8) & 0xFF; // High byte of 10-bit value
    bitSet(TIFR4, OCF4B);                                     // Clear pending interrupt flags if any
    OCR4B = ir_signal_send_current_token_timing & 0xFF;       // Low byte of 10-bit value
    bitSet(TIMSK4, OCIE4B);                                   // Enable rising edge interrupt
  }
  else
  {
    ir_signal_send_current_token_timing += ir_signal_spacing;
    TC4H = (ir_signal_send_current_token_timing >> 8) & 0xFF; // High byte of 10-bit value
    bitSet(TIFR4, OCF4D);                                     // Clear pending interrupt flags if any
    OCR4D = ir_signal_send_current_token_timing & 0xFF;       // Low byte of 10-bit value
    bitSet(TIMSK4, OCIE4D);                                   // Enable signal spacing period interrupt
#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
    ir_led_token_active = false;
// #ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR_DEBUG_PIN_D2
// bitClear(PORT_DEBUG_PORT_D2, DEBUG_PORT_D2); // IR LED token ended
// #endif
#endif
  }
  bitClear(TIMSK4, OCIE4A); // Disable this interrupt
}

ISR(TIMER4_COMPB_vect) // IR pulse rising edge
{
  bitSet(PORT_LED_IR_D3, LED_IR_D3);
  ir_signal_send_current_token_timing += ir_signal_send_current_timings[ir_signal_send_current_token_position++];
  if (TCNT4 < ir_signal_send_current_token_timing - 5)
  {
    TC4H = (ir_signal_send_current_token_timing >> 8) & 0xFF; // High byte of 10-bit value
    bitSet(TIFR4, OCF4A);                                     // Clear pending interrupt flags if any
    OCR4A = ir_signal_send_current_token_timing & 0xFF;       // Low byte of 10-bit value
    bitSet(TIMSK4, OCIE4A);                                   // Enable falling edge interrupt
  }
  else
  {
    // If its within 5 microseconds abort this ir signal as its probably already malformed and we don't want to miss the off signal...
    bitClear(PORT_LED_IR_D3, LED_IR_D3);
    ir_signal_send_current_token_timing += ir_signal_spacing;
    TC4H = (ir_signal_send_current_token_timing >> 8) & 0xFF; // High byte of 10-bit value
    bitSet(TIFR4, OCF4D);                                     // Clear pending interrupt flags if any
    OCR4D = ir_signal_send_current_token_timing & 0xFF;       // Low byte of 10-bit value
    bitSet(TIMSK4, OCIE4D);                                   // Enable signal spacing period interrupt
#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
    ir_led_token_active = false;
// #ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR_DEBUG_PIN_D2
// bitClear(PORT_DEBUG_PORT_D2, DEBUG_PORT_D2); // IR LED token ended
// #endif
#endif
  }
  bitClear(TIMSK4, OCIE4B); // Disable this interrupt
}

ISR(TIMER4_COMPD_vect) // IR signal spacing period finished
{
  TCCR4B = 0;
  ir_signal_send_finished();
  bitClear(TIMSK4, OCIE4D); // Disable this interrupt
}

void ir_signal_send_request(ir_signal_type signal)
{
  /*
  // Record the time open signals are sent
  if (signal == SIGNAL_OPEN_RIGHT) {
    cli();
    ir_signal_send_last_open_right_tcnt1 = TCNT1;
    sei();
  }
  else if (signal == SIGNAL_OPEN_LEFT) {
    cli();
    ir_signal_send_last_open_left_tcnt1 = TCNT1;
    sei();
  }
  */
  // Check if a send operation is in progress
  if (ir_signal_send_in_progress)
  {
    cli();
    // Check if the circular queue is not full
    if ((ir_signal_send_circular_queue_end + 1) % SIGNAL_SEND_QUEUE_SIZE != ir_signal_send_circular_queue_position)
    {
      // Add the signal to the circular queue
      ir_signal_send_circular_queue[ir_signal_send_circular_queue_end] = signal;
      ir_signal_send_circular_queue_end = (ir_signal_send_circular_queue_end + 1) % SIGNAL_SEND_QUEUE_SIZE;
    }
    else
    {
      // Circular queue is full, handle accordingly (e.g., drop the signal or handle an overflow condition)
    }
    sei();
  }
  else
  {
    // No send operation in progress, start sending immediately
    ir_signal_send(signal);
    // Set the send_in_progress flag
    ir_signal_send_in_progress = true;
  }
}

void ir_signal_send_finished()
{
  ir_signal_send_current_signal = SIGNAL_NONE;
  // Check if there are any pending send operations in the circular buffer
  if (ir_signal_send_circular_queue_position != ir_signal_send_circular_queue_end)
  {
    // Get the next signal from the circular queue
    ir_signal_type next_signal = ir_signal_send_circular_queue[ir_signal_send_circular_queue_position];
    // Increment the circular queue position
    ir_signal_send_circular_queue_position = (ir_signal_send_circular_queue_position + 1) % SIGNAL_SEND_QUEUE_SIZE;

    // Start sending the next signal
    ir_signal_send(next_signal);
  }
  else
  {
    // No pending send operations, set the send_in_progress flag to false
    ir_signal_send_in_progress = false;
  }
}

/*
ISR(TIMER1_COMPA_vect)
{

}
//*/

ISR(TIMER1_COMPB_vect)
{
  ir_signal_type scheduled_signal = ir_signal_next_timer1_compb_scheduled_signal;
  uint8_t scheduled_signal_index;
  const ir_signal_t *scheduled_signal_definition;
  uint16_t scheduled_signal_time_temp = 0;
  scheduled_signal_index = ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signal_index[scheduled_signal];
  if (scheduled_signal_index != 255 && scheduled_signal_index < ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signal_count)
  {
    scheduled_signal_definition = &(ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signals[scheduled_signal_index]);
    if (scheduled_signal_definition->mode == 1)
    {
      scheduled_signal_time_temp = scheduled_signal_definition->token_length;
    }
  }

  if (scheduled_signal == SIGNAL_OPEN_LEFT)
  {
    if (ir_average_timing_mode == 1 && ir_average_timing_mode_stop[1] == true) // If average timing mode has been stopped we are not going to execute the signal so we don't need to schedule a correspond close
    {
      ir_signal_next_timer1_compb_scheduled_signal = SIGNAL_NONE;
      ir_average_timing_mode_stop[1] = false;
      ir_average_timing_mode_running[1] = false;
      bitClear(TIMSK1, OCIE1B);
    }
    else
    {
      ir_signal_next_timer1_compb_scheduled_signal = SIGNAL_CLOSE_LEFT;
      ir_average_timing_mode_last_open_timer1_tcnt[1] = OCR1B - (ir_frame_delay << 1) + scheduled_signal_time_temp; // not sure if the token_length we are using here is the right one
      scheduled_signal_time_temp = OCR1B + ((ir_frame_duration - scheduled_signal_time_temp) << 1);
      OCR1B = scheduled_signal_time_temp;
      ir_average_timing_mode_last_open_timer1_tcnt_set[1] = true;
      ir_signal_send_request(scheduled_signal);
    }
  }
  else
  {
    if (ir_average_timing_mode == 1 && ir_average_timing_mode_stop[1] == false && ir_average_timing_mode_no_trigger_counter < MAX_SIGNALS_TO_GENERATE_WITHOUT_TRIGGER)
    {
      if (ir_signal_trigger_frametime_average_effective_counter % 2 == 0)
      {
        ir_signal_trigger_frametime_average_effective = ir_signal_trigger_frametime_average;
      }
      ir_signal_next_timer1_compb_scheduled_signal = ir_signal_next_timer1_compb_start_signal;
      scheduled_signal_time_temp = OCR1B + (((ir_signal_trigger_frametime_average_effective << 1) - ir_frame_duration + ir_signal_trigger_frame_delay_adjustment[1] - scheduled_signal_time_temp) << 1);
      ir_signal_trigger_frame_delay_adjustment[1] = 0; // we set this back to 0 each time because the adjustment has been made
      OCR1B = scheduled_signal_time_temp;
      ir_average_timing_mode_no_trigger_counter++;
      ir_signal_trigger_frametime_average_effective_counter++;
    }
    else
    {
      ir_signal_next_timer1_compb_scheduled_signal = SIGNAL_NONE;
      ir_average_timing_mode_stop[1] = false;
      ir_average_timing_mode_running[1] = false;
      bitClear(TIMSK1, OCIE1B);
    }
    ir_signal_send_request(scheduled_signal);
  }
}

ISR(TIMER1_COMPC_vect)
{
  ir_signal_type scheduled_signal = ir_signal_next_timer1_compc_scheduled_signal;
  uint8_t scheduled_signal_index;
  const ir_signal_t *scheduled_signal_definition;
  uint16_t scheduled_signal_time_temp = 0;
  scheduled_signal_index = ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signal_index[scheduled_signal];
  if (scheduled_signal_index != 255 && scheduled_signal_index < ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signal_count)
  {
    scheduled_signal_definition = &(ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signals[scheduled_signal_index]);
    if (scheduled_signal_definition->mode == 1)
    {
      scheduled_signal_time_temp = scheduled_signal_definition->token_length;
    }
  }
  if (scheduled_signal == SIGNAL_OPEN_RIGHT)
  {
    if (ir_average_timing_mode == 1 && ir_average_timing_mode_stop[0] == true) // If average timing mode has been stopped we are not going to execute the signal so we don't need to schedule a correspond close
    {
      ir_signal_next_timer1_compc_scheduled_signal = SIGNAL_NONE;
      ir_average_timing_mode_stop[0] = false;
      ir_average_timing_mode_running[0] = false;
      bitClear(TIMSK1, OCIE1C);
    }
    else
    {
      ir_signal_next_timer1_compc_scheduled_signal = SIGNAL_CLOSE_RIGHT;
      ir_average_timing_mode_last_open_timer1_tcnt[0] = OCR1C - (ir_frame_delay << 1) + scheduled_signal_time_temp; // not sure if the token_length we are using here is the right one
      scheduled_signal_time_temp = OCR1C + ((ir_frame_duration - scheduled_signal_time_temp) << 1);
      OCR1C = scheduled_signal_time_temp;
      ir_average_timing_mode_last_open_timer1_tcnt_set[0] = true;
      ir_signal_send_request(scheduled_signal);
    }
  }
  else
  {
    if (ir_average_timing_mode == 1 && ir_average_timing_mode_stop[0] == false && ir_average_timing_mode_no_trigger_counter < MAX_SIGNALS_TO_GENERATE_WITHOUT_TRIGGER)
    {
      if (ir_signal_trigger_frametime_average_effective_counter % 2 == 0)
      {
        ir_signal_trigger_frametime_average_effective = ir_signal_trigger_frametime_average;
      }
      ir_signal_next_timer1_compc_scheduled_signal = ir_signal_next_timer1_compc_start_signal;
      scheduled_signal_time_temp = OCR1C + (((ir_signal_trigger_frametime_average_effective << 1) - ir_frame_duration + ir_signal_trigger_frame_delay_adjustment[0] - scheduled_signal_time_temp) << 1);
      ir_signal_trigger_frame_delay_adjustment[0] = 0; // we set this back to 0 each time because the adjustment has been made
      OCR1C = scheduled_signal_time_temp;
      ir_average_timing_mode_no_trigger_counter++;
      ir_signal_trigger_frametime_average_effective_counter++;
    }
    else
    {
      ir_signal_next_timer1_compc_scheduled_signal = SIGNAL_NONE;
      ir_average_timing_mode_stop[0] = false;
      ir_average_timing_mode_running[0] = false;
      bitClear(TIMSK1, OCIE1C);
    }
    ir_signal_send_request(scheduled_signal);
  }
}

/*
 Responsible for converting external state change parameters into the those parameters used internally.
 Schedule the open signal for the current frames eye.
*/
void ir_signal_process_trigger(uint8_t left_eye)
{
  ir_signal_type ir_desired_signal = (left_eye ^ ir_flip_eyes ? SIGNAL_OPEN_LEFT : SIGNAL_OPEN_RIGHT);

  uint8_t desired_signal_index;
  ir_glasses_selected_library = ir_glasses_available[ir_glasses_selected];
  desired_signal_index = ir_glasses_selected_library->signal_index[ir_desired_signal];
  if (desired_signal_index > ir_glasses_selected_library->signal_count || desired_signal_index == 255)
  {
    ir_desired_signal = (left_eye ^ ir_flip_eyes ? SIGNAL_OPEN_LEFT_CLOSE_RIGHT : SIGNAL_OPEN_RIGHT_CLOSE_LEFT);
    desired_signal_index = ir_glasses_selected_library->signal_index[ir_desired_signal];
    if (desired_signal_index > ir_glasses_selected_library->signal_count || desired_signal_index == 255)
    {
      return;
    }
  }
  cli();
  ir_signal_trigger_current_timer1_tcnt = TCNT1;
  sei();

  if (ir_average_timing_mode == 1)
  {
    cli();
    ir_average_timing_mode_no_trigger_counter = 0;
    sei();

    ir_signal_trigger_current_time = micros();

    if (ir_signal_trigger_last_time_set == true)
    {
      uint16_t new_frametime = ir_signal_trigger_current_time - ir_signal_trigger_last_time;

      if (new_frametime > (target_frametime << 1))
      {
        // no updates for more than 1 frame reset all averaging counters.
        ir_signal_trigger_frametime_average_set = false;
        ir_signal_trigger_frametime_average_shifted = 0;
        cli();
        ir_average_timing_mode_last_open_timer1_tcnt[0] = 0;
        ir_average_timing_mode_last_open_timer1_tcnt[1] = 0;
        ir_average_timing_mode_last_open_timer1_tcnt_set[0] = false;
        ir_average_timing_mode_last_open_timer1_tcnt_set[1] = false;
        ir_signal_trigger_frametime_average = 0;
        ir_signal_trigger_frametime_average_effective = 0;
        ir_signal_trigger_frametime_average_effective_counter = 0;
        ir_signal_trigger_frame_delay_adjustment[0] = 0;
        ir_signal_trigger_frame_delay_adjustment[1] = 0;
        ir_average_timing_mode_running[0] = false;
        ir_average_timing_mode_running[1] = false;
        sei();
      }

      if (ir_signal_trigger_frametime_average_set)
      {
        // Rolling average update using bit shifting (normalized)
        uint32_t new_ir_signal_trigger_frametime_average_shifted = ir_signal_trigger_frametime_average_shifted - (ir_signal_trigger_frametime_average_shifted >> FRAME_HISTORY_SHIFT);
        new_ir_signal_trigger_frametime_average_shifted += new_frametime;

        // Ensure new_frametime is within 30 microseconds of the target before updating (unless we have no target frame time or we are still initializing)
        if (target_frametime == 0 || (new_frametime >= target_frametime - 50 && new_frametime <= target_frametime + 50))
        {
          ir_signal_trigger_frametime_average_shifted = new_ir_signal_trigger_frametime_average_shifted;
          cli();
          ir_signal_trigger_frametime_average = new_ir_signal_trigger_frametime_average_shifted >> FRAME_HISTORY_SHIFT;
          sei();
        }

        if (ir_average_timing_mode_last_open_timer1_tcnt_set[left_eye])
        {
          // snapshot teh variables that might change in ISRs
          cli();
          uint16_t temp_ir_signal_trigger_frametime_average_effective = ir_signal_trigger_frametime_average_effective;
          uint16_t temp_ir_average_timing_mode_last_open_timer1_tcnt[2];
          int16_t temp_ir_signal_trigger_frame_delay_adjustment[2];
          temp_ir_average_timing_mode_last_open_timer1_tcnt[0] = ir_average_timing_mode_last_open_timer1_tcnt[0];
          temp_ir_average_timing_mode_last_open_timer1_tcnt[1] = ir_average_timing_mode_last_open_timer1_tcnt[1];
          sei();
          temp_ir_signal_trigger_frame_delay_adjustment[0] = 0;
          temp_ir_signal_trigger_frame_delay_adjustment[1] = 0;

          uint16_t expected_time = (temp_ir_average_timing_mode_last_open_timer1_tcnt[left_eye]) + (temp_ir_signal_trigger_frametime_average_effective << 2); // tcnt in timer units and frametime is in microseconds but needs to doubled for a full left right cycle as it is the display refresh frame time, then doubled again to make it into timer units.
          int16_t time_error = ((int16_t)(ir_signal_trigger_current_timer1_tcnt - expected_time)) >> 1;
          bool temp_detected_dropped_frame = false;
          // check if the ir_average_timing_mode_last_open_timer1_tcnt is from the same cycle as ir_signal_trigger_current_timer1_tcnt, otherwise we need to shift it back or forward.
          if (time_error < (-((int16_t)temp_ir_signal_trigger_frametime_average_effective) - ((int16_t)temp_ir_signal_trigger_frametime_average_effective >> 1)))
          {
            time_error += (temp_ir_signal_trigger_frametime_average_effective << 1);
          }
          if (time_error >= (((int16_t)temp_ir_signal_trigger_frametime_average_effective) - 1000) && time_error <= ((int16_t)temp_ir_signal_trigger_frametime_average_effective) + 1000)
          {
            temp_detected_dropped_frame = true;
          }
          else if (time_error >= (-((int16_t)temp_ir_signal_trigger_frametime_average_effective) - 1000) && time_error <= -((int16_t)temp_ir_signal_trigger_frametime_average_effective) + 1000)
          {
            temp_detected_dropped_frame = true;
          }
          else
          {
            temp_ir_signal_trigger_frame_delay_adjustment[0] = time_error >> 4; // Otherwise applya a correction (~1/16th of error)
            // temp_ir_signal_trigger_frame_delay_adjustment[0] = time_error >> 5; // Otherwise applya a correction (~1/32nd of error)
            temp_ir_signal_trigger_frame_delay_adjustment[1] = temp_ir_signal_trigger_frame_delay_adjustment[0];
          }

          int16_t diff_time_left_right = 0;
          int16_t diff_time_right_left = 0;
          //*
          if (!temp_detected_dropped_frame)
          {
            // differential timing adjustment left and right
            cli();
            diff_time_left_right = (int16_t)((temp_ir_average_timing_mode_last_open_timer1_tcnt[1]) - (temp_ir_average_timing_mode_last_open_timer1_tcnt[0]) - (temp_ir_signal_trigger_frametime_average_effective << 1)) >> 1;
            diff_time_right_left = (int16_t)((temp_ir_average_timing_mode_last_open_timer1_tcnt[0]) - (temp_ir_average_timing_mode_last_open_timer1_tcnt[1]) - (temp_ir_signal_trigger_frametime_average_effective << 1)) >> 1;
            sei();
            if (diff_time_left_right > -5000 && diff_time_left_right < 5000)
            {
              // because we adjust both we only need half for each, and we also only apply half the adjustment factor incase there is something wrong.
              temp_ir_signal_trigger_frame_delay_adjustment[0] += diff_time_left_right >> 2;
              temp_ir_signal_trigger_frame_delay_adjustment[1] -= diff_time_left_right >> 2;
            }
            else if (diff_time_right_left > -5000 && diff_time_right_left < 5000)
            {
              // because we adjust both we only need half for each, and we also only apply half the adjustment factor incase there is something wrong.
              temp_ir_signal_trigger_frame_delay_adjustment[0] -= diff_time_right_left >> 2;
              temp_ir_signal_trigger_frame_delay_adjustment[1] += diff_time_right_left >> 2;
            }
          }
          //*/

          cli();
          ir_signal_trigger_frame_delay_adjustment[0] += temp_ir_signal_trigger_frame_delay_adjustment[0];
          ir_signal_trigger_frame_delay_adjustment[1] += temp_ir_signal_trigger_frame_delay_adjustment[1];
          //*
          if (temp_detected_dropped_frame)
          {
            // On duplicate just bump the comparators and last updates by one frame cycle
            OCR1B += ir_signal_trigger_frametime_average << 1;
            OCR1C += ir_signal_trigger_frametime_average << 1;
            ir_average_timing_mode_last_open_timer1_tcnt[0] += ir_signal_trigger_frametime_average << 1;
            ir_average_timing_mode_last_open_timer1_tcnt[1] += ir_signal_trigger_frametime_average << 1;
            ir_signal_trigger_frame_delay_adjustment[0] = 0;
            ir_signal_trigger_frame_delay_adjustment[1] = 0;
          }
          //*/
          sei();

#ifdef DEBUG_AVERAGE_TIMING_MODE
          ir_signal_trigger_logger_counter++;
          if (ir_signal_trigger_logger_counter % 1 == 0)
          // if (ir_signal_trigger_logger_counter <= 10)
          {
            // Serial.print(ir_signal_trigger_current_time);
            // Serial.print(",");
            Serial.print(left_eye);
            Serial.print(",");
            Serial.print(temp_ir_average_timing_mode_last_open_timer1_tcnt[0]);
            Serial.print(",");
            Serial.print(temp_ir_average_timing_mode_last_open_timer1_tcnt[1]);
            Serial.print(",");
            Serial.print(temp_ir_signal_trigger_frametime_average_effective);
            Serial.print(",");
            Serial.print(ir_signal_trigger_current_timer1_tcnt);
            Serial.print(",");
            Serial.print(expected_time);
            Serial.print(",");
            Serial.print(time_error);
            Serial.print(",");
            Serial.print(diff_time_left_right);
            Serial.print(",");
            Serial.print(diff_time_right_left);
            Serial.print(",");
            Serial.print(temp_ir_signal_trigger_frame_delay_adjustment[0]);
            Serial.print(",");
            Serial.print(temp_ir_signal_trigger_frame_delay_adjustment[1]);
            // Serial.print(",");
            // Serial.print(ir_signal_trigger_frametime_average_shifted >> FRAME_HISTORY_SHIFT);
            Serial.println();
          }
#endif
        }
      }
      else
      {
        if (target_frametime == 0 || (new_frametime >= target_frametime - 100 && new_frametime <= target_frametime + 100))
        {
          ir_signal_trigger_frametime_average_shifted = ((uint32_t)new_frametime) << FRAME_HISTORY_SHIFT; // Store unnormalized value
          ir_signal_trigger_frametime_average_set = true;
          cli();
          ir_signal_trigger_frametime_average = new_frametime;
          ir_signal_trigger_frame_delay_adjustment[0] = 0;
          ir_signal_trigger_frame_delay_adjustment[1] = 0;
          sei();
        }
      }
    }

    ir_signal_trigger_last_time = ir_signal_trigger_current_time;
    ir_signal_trigger_last_timer1_tcnt = ir_signal_trigger_current_timer1_tcnt;
    ir_signal_trigger_last_time_set = true;
  }

  if (ir_average_timing_mode == 0 || ir_average_timing_mode_running[left_eye] == false)
  {
    if (ir_average_timing_mode == 1 && ir_signal_trigger_frametime_average_set == true)
    {
      ir_average_timing_mode_running[left_eye] = true;

#ifdef DEBUG_AVERAGE_TIMING_MODE
      ir_signal_trigger_logger_counter = 0;
      // Serial.print("ir_signal_trigger_current_time");
      // Serial.print(",");
      Serial.print("is_left_eye");
      Serial.print(",");
      Serial.print("temp_ir_average_timing_mode_last_open_timer1_tcnt[0]");
      Serial.print(",");
      Serial.print("temp_ir_average_timing_mode_last_open_timer1_tcnt[1]");
      Serial.print(",");
      Serial.print("temp_ir_signal_trigger_frametime_average_effective");
      Serial.print(",");
      Serial.print("ir_signal_trigger_current_timer1_tcnt");
      Serial.print(",");
      Serial.print("expected_time");
      Serial.print(",");
      Serial.print("time_error");
      Serial.print(",");
      Serial.print("diff_time_left_right");
      Serial.print(",");
      Serial.print("diff_time_right_left");
      Serial.print(",");
      Serial.print("temp_ir_signal_trigger_frame_delay_adjustment[0]");
      Serial.print(",");
      Serial.print("temp_ir_signal_trigger_frame_delay_adjustment[1]");
      // Serial.print(",");
      // Serial.print("ir_signal_trigger_frametime_average_shifted >> FRAME_HISTORY_SHIFT");
      Serial.println();
#endif
    }
    uint16_t timer1_tcnt_target = ir_signal_trigger_current_timer1_tcnt + (ir_frame_delay << 1);

    uint8_t scheduled_signal_index;
    const ir_signal_t *scheduled_signal_definition;

    if (ir_glasses_selected_library != ir_glasses_selected_library_sub_ir_signal_schedule_send_request)
    {
      // If the selected glasses have changed we need to stop everything.
      // ir_signal_next_timer1_compb_scheduled_signal = SIGNAL_NONE;
      bitClear(TIMSK1, OCIE1B);
      bitSet(TIFR1, OCF1B);
      ir_average_timing_mode_last_open_timer1_tcnt_set[1] = false;
      ir_signal_trigger_frame_delay_adjustment[1] = 0;
      ir_average_timing_mode_running[1] = false;
      // ir_signal_next_timer1_compc_scheduled_signal = SIGNAL_NONE;
      bitClear(TIMSK1, OCIE1C);
      bitSet(TIFR1, OCF1C);
      ir_average_timing_mode_last_open_timer1_tcnt_set[0] = false;
      ir_signal_trigger_frame_delay_adjustment[0] = 0;
      ir_average_timing_mode_running[0] = false;
    }
    ir_glasses_selected_library_sub_ir_signal_schedule_send_request = ir_glasses_selected_library;
    scheduled_signal_index = ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signal_index[ir_desired_signal];
    if (scheduled_signal_index != 255 && scheduled_signal_index < ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signal_count)
    {
      scheduled_signal_definition = &(ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signals[scheduled_signal_index]);
      if (scheduled_signal_definition->mode == 1)
      {
        timer1_tcnt_target -= scheduled_signal_definition->token_length;
      }
    }

    if (ir_desired_signal == SIGNAL_OPEN_LEFT || ir_desired_signal == SIGNAL_OPEN_LEFT_CLOSE_RIGHT)
    {
      if (ir_signal_next_timer1_compb_scheduled_signal == SIGNAL_NONE)
      {
        cli();
        OCR1B = timer1_tcnt_target;
        bitSet(TIFR1, OCF1B);
        bitSet(TIMSK1, OCIE1B);
        ir_signal_next_timer1_compb_scheduled_signal = ir_desired_signal;
        ir_signal_next_timer1_compb_start_signal = ir_desired_signal;
        ir_signal_next_timer1_compb_start_time = timer1_tcnt_target;
        sei();
      }
    }
    else if ((ir_desired_signal == SIGNAL_OPEN_RIGHT || ir_desired_signal == SIGNAL_OPEN_RIGHT_CLOSE_LEFT))
    {
      if (ir_signal_next_timer1_compc_scheduled_signal == SIGNAL_NONE)
      {
        cli();
        OCR1C = timer1_tcnt_target;
        bitSet(TIFR1, OCF1C);
        bitSet(TIMSK1, OCIE1C);
        ir_signal_next_timer1_compc_scheduled_signal = ir_desired_signal;
        ir_signal_next_timer1_compc_start_signal = ir_desired_signal;
        ir_signal_next_timer1_compc_start_time = timer1_tcnt_target;
        sei();
      }
    }
  }
}
