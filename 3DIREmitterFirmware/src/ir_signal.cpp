/*
* Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
*/

#include <Arduino.h>

#include "settings.h"
#include "ir_signal.h"
#include "ir_glasses.h"

volatile uint8_t ir_glasses_selected = 6;
volatile uint16_t ir_frame_duration = IR_FRAME_DURATION;
volatile uint16_t ir_frame_delay = IR_FRAME_DELAY;
volatile uint16_t ir_signal_spacing = IR_SIGNAL_SPACING;
volatile uint8_t ir_flip_eyes = 0;
#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
volatile bool ir_led_token_active = false;
#endif

const ir_glasses_signal_library_t* ir_glasses_selected_library;
const ir_glasses_signal_library_t* ir_glasses_selected_library_sub_ir_signal_schedule_send_request;
const ir_glasses_signal_library_t* ir_glasses_selected_library_sub_ir_signal_send;
volatile ir_signal_type ir_signal_send_circular_queue[SIGNAL_SEND_QUEUE_SIZE];
volatile uint8_t ir_signal_send_circular_queue_position = 0;
volatile uint8_t ir_signal_send_circular_queue_end = 0;
volatile bool ir_signal_send_in_progress = false;
ir_signal_type ir_signal_send_current_signal = SIGNAL_NONE;
const ir_signal_t* ir_signal_send_current_definition;
const uint16_t* ir_signal_send_current_timings;
uint8_t ir_signal_send_current_token_position;
uint8_t ir_signal_send_current_token_length;
uint16_t ir_signal_send_current_token_timing;
uint16_t ir_signal_send_last_open_right_tcnt1;
uint16_t ir_signal_send_last_open_left_tcnt1;
ir_signal_type ir_signal_next_timer1_compa_signal = SIGNAL_NONE;
ir_signal_type ir_signal_next_timer1_compa_next_signal = SIGNAL_NONE;
uint16_t ir_signal_next_timer1_compa_next_time = SIGNAL_NONE;
ir_signal_type ir_signal_next_timer1_compb_signal = SIGNAL_NONE;
ir_signal_type ir_signal_next_timer1_compb_next_signal = SIGNAL_NONE;
uint16_t ir_signal_next_timer1_compb_next_time = SIGNAL_NONE;
ir_signal_type ir_signal_next_timer1_compc_signal = SIGNAL_NONE;


// This should initialize timer1 for sending ir signals and timer4 for scheduling 
// ir signals on both left and right eyes using two different comparators.
void ir_signal_init() {
  ir_glasses_selected = 6;
  ir_frame_duration = IR_FRAME_DURATION;
  ir_frame_delay = IR_FRAME_DELAY;
  ir_signal_spacing = IR_SIGNAL_SPACING;
  ir_flip_eyes = 0;
  #ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
  ir_led_token_active = false; 
  #endif

  for (uint8_t i = 0; i < SIGNAL_SEND_QUEUE_SIZE; i++) {
    ir_signal_send_circular_queue[i] = SIGNAL_NONE;
  }
  ir_signal_send_circular_queue_position = 0;
  ir_signal_send_circular_queue_end = 0;
  ir_signal_send_in_progress = false;
  ir_signal_send_current_signal = SIGNAL_NONE;
  ir_signal_next_timer1_compa_signal = SIGNAL_NONE;
  ir_signal_next_timer1_compb_signal = SIGNAL_NONE;
  ir_signal_next_timer1_compc_signal = SIGNAL_NONE;
  ir_signal_next_timer1_compa_next_signal = SIGNAL_NONE;
  ir_signal_next_timer1_compa_next_time = 0;
  ir_signal_next_timer1_compb_next_signal = SIGNAL_NONE;
  ir_signal_next_timer1_compb_next_time = 0;

  // Initialize timer1 for scheduling IR signal sends
  TCCR1C = 0; // Timer stopped, normal mode
  TCCR1B = 0;
  TCCR1A = 0;
  TIMSK1 = 0; // All interrupts disabled
  //bitSet(TIMSK1, TOIE1); // Enable TCNT1 overflow interrupt
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
  //bitSet(TIMSK4, TOIE4); // Enable TCNT4 overflow interrupt
  TIFR4 = 0xFF; // Clear pending interrupt flags if any
}

/* 
 This should take a specific signal and start the ir transmission immediately 
 It should be called from two places.
 1) from ir_signal_process_opt_sensor when we detect a duplicate frame to send a fast switch signal.
 2) from the comparator isr used by ir_signal_schedule_send
*/
void ir_signal_send(ir_signal_type signal) {
  uint8_t signal_index;
  ir_glasses_selected_library_sub_ir_signal_send = ir_glasses_selected_library_sub_ir_signal_schedule_send_request;
  signal_index = ir_glasses_selected_library_sub_ir_signal_send->signal_index[signal];
  if (signal_index != 255 && signal_index < ir_glasses_selected_library_sub_ir_signal_send->signal_count) {
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
      bitClear(PORT_DEBUG_PORT_D15, DEBUG_PORT_D15);
    }
    if (signal == SIGNAL_OPEN_RIGHT || signal == SIGNAL_OPEN_RIGHT_CLOSE_LEFT || signal == SIGNAL_OPEN_RIGHT_FAST_SWAP)
    {
      bitSet(PORT_DEBUG_ACTIVATE_RIGHT_D8, DEBUG_ACTIVATE_RIGHT_D8);
    }
    else if (signal == SIGNAL_OPEN_LEFT_CLOSE_RIGHT || signal == SIGNAL_CLOSE_RIGHT)
    {
      bitClear(PORT_DEBUG_ACTIVATE_RIGHT_D8, DEBUG_ACTIVATE_RIGHT_D8);
      bitClear(PORT_DEBUG_PORT_D15, DEBUG_PORT_D15);
    }
    if (signal == SIGNAL_OPEN_LEFT_FAST_SWAP || signal == SIGNAL_OPEN_RIGHT_FAST_SWAP) {
      bitSet(PORT_DEBUG_PORT_D15, DEBUG_PORT_D15);
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
    if (ir_signal_send_current_token_timing > 0) {
      TC4H = (ir_signal_send_current_token_timing >> 8) & 0xFF; // High byte of 10-bit value
      OCR4A = ir_signal_send_current_token_timing & 0xFF; // Low byte of 10-bit value
      bitSet(TIMSK4, OCIE4A); // Enable IR pulse falling edge interrupt
      bitSet(PORT_LED_IR_D3, LED_IR_D3);
    } 
    else {
      if (ir_signal_send_current_token_position < ir_signal_send_current_token_length) {
        ir_signal_send_current_token_timing += ir_signal_send_current_timings[ir_signal_send_current_token_position++];
        TC4H = (ir_signal_send_current_token_timing >> 8) & 0xFF; // High byte of 10-bit value
        OCR4B = ir_signal_send_current_token_timing & 0xFF; // Low byte of 10-bit value
        bitSet(TIMSK4, OCIE4B); // Enable rising edge interrupt
      } else {
        ir_signal_send_current_token_timing += ir_signal_spacing;
        TC4H = (ir_signal_send_current_token_timing >> 8) & 0xFF; // High byte of 10-bit value
        OCR4D = ir_signal_send_current_token_timing & 0xFF; // Low byte of 10-bit value
        bitSet(TIMSK4, OCIE4D); // Enable signal spacing period interrupt
        #ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
        ir_led_token_active = false;
        //#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR_DEBUG_PIN_D2
        //bitClear(PORT_DEBUG_PORT_D2, DEBUG_PORT_D2); // IR LED token ended
        //#endif
        #endif
      }
    }
    TIFR4 = 0xFF; // Clear pending interrupts if any
    TCCR4B = _BV(CS42) | _BV(CS40); // prescaler 16x
    //TCCR4B = _BV(CS42); // prescaler 8x
    sei();
  } else {
    // The selected glasses don't support the requested signal.
    ir_signal_send_finished();
    return;
  }
}

ISR(TIMER4_COMPA_vect) // IR pulse falling edge
{
  bitClear(PORT_LED_IR_D3, LED_IR_D3);
  if (ir_signal_send_current_token_position < ir_signal_send_current_token_length) {
    ir_signal_send_current_token_timing += ir_signal_send_current_timings[ir_signal_send_current_token_position++];
    TC4H = (ir_signal_send_current_token_timing >> 8) & 0xFF; // High byte of 10-bit value
    bitSet(TIFR4, OCF4B); // Clear pending interrupt flags if any
    OCR4B = ir_signal_send_current_token_timing & 0xFF; // Low byte of 10-bit value
    bitSet(TIMSK4, OCIE4B); // Enable rising edge interrupt
  } else {
    ir_signal_send_current_token_timing += ir_signal_spacing;
    TC4H = (ir_signal_send_current_token_timing >> 8) & 0xFF; // High byte of 10-bit value
    bitSet(TIFR4, OCF4D); // Clear pending interrupt flags if any
    OCR4D = ir_signal_send_current_token_timing & 0xFF; // Low byte of 10-bit value
    bitSet(TIMSK4, OCIE4D); // Enable signal spacing period interrupt
    #ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
    ir_led_token_active = false;
    //#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR_DEBUG_PIN_D2
    //bitClear(PORT_DEBUG_PORT_D2, DEBUG_PORT_D2); // IR LED token ended
    //#endif
    #endif
  }
  bitClear(TIMSK4, OCIE4A); // Disable this interrupt
}

ISR(TIMER4_COMPB_vect) // IR pulse rising edge
{
  bitSet(PORT_LED_IR_D3, LED_IR_D3);
  ir_signal_send_current_token_timing += ir_signal_send_current_timings[ir_signal_send_current_token_position++];
  if (TCNT4 < ir_signal_send_current_token_timing - 5) {
    TC4H = (ir_signal_send_current_token_timing >> 8) & 0xFF; // High byte of 10-bit value
    bitSet(TIFR4, OCF4A); // Clear pending interrupt flags if any
    OCR4A = ir_signal_send_current_token_timing & 0xFF; // Low byte of 10-bit value
    bitSet(TIMSK4, OCIE4A); // Enable falling edge interrupt
  }
  else {
    // If its within 5 microseconds abort this ir signal as its probably already malformed and we don't want to miss the off signal...
    bitClear(PORT_LED_IR_D3, LED_IR_D3);
    ir_signal_send_current_token_timing += ir_signal_spacing;
    TC4H = (ir_signal_send_current_token_timing >> 8) & 0xFF; // High byte of 10-bit value
    bitSet(TIFR4, OCF4D); // Clear pending interrupt flags if any
    OCR4D = ir_signal_send_current_token_timing & 0xFF; // Low byte of 10-bit value
    bitSet(TIMSK4, OCIE4D); // Enable signal spacing period interrupt
    #ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR
    ir_led_token_active = false;
    //#ifdef OPT_SENSOR_ENABLE_IGNORE_DURING_IR_DEBUG_PIN_D2
    //bitClear(PORT_DEBUG_PORT_D2, DEBUG_PORT_D2); // IR LED token ended
    //#endif
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

void ir_signal_send_request(ir_signal_type signal) {
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
  if (ir_signal_send_in_progress) {
    cli();
    // Check if the circular queue is not full
    if ((ir_signal_send_circular_queue_end + 1) % SIGNAL_SEND_QUEUE_SIZE != ir_signal_send_circular_queue_position) {
      // Add the signal to the circular queue
      ir_signal_send_circular_queue[ir_signal_send_circular_queue_end] = signal;
      ir_signal_send_circular_queue_end = (ir_signal_send_circular_queue_end + 1) % SIGNAL_SEND_QUEUE_SIZE;
    } else {
      // Circular queue is full, handle accordingly (e.g., drop the signal or handle an overflow condition)
    }
    sei();
  } else {
    // No send operation in progress, start sending immediately
    ir_signal_send(signal);
    // Set the send_in_progress flag
    ir_signal_send_in_progress = true;
  }
}

void ir_signal_send_finished() {
  ir_signal_send_current_signal = SIGNAL_NONE;
  // Check if there are any pending send operations in the circular buffer
  if (ir_signal_send_circular_queue_position != ir_signal_send_circular_queue_end) {
    // Get the next signal from the circular queue
    ir_signal_type next_signal = ir_signal_send_circular_queue[ir_signal_send_circular_queue_position];
    // Increment the circular queue position
    ir_signal_send_circular_queue_position = (ir_signal_send_circular_queue_position + 1) % SIGNAL_SEND_QUEUE_SIZE;
    
    // Start sending the next signal
    ir_signal_send(next_signal);
  } else {
    // No pending send operations, set the send_in_progress flag to false
    ir_signal_send_in_progress = false;
  }
}


/*
 this should take the signal to queue up and it will be loaded into a comparator on timer 4,
 based on the frame delay (for open signal) and frame duration (for close signal).
 Which of the two used comparators will depend on which eye it is for.

 It should be called in two scenarios.
 1) It will be called from the comparator isr 
    (when an open signal is processed to queue the corresponding closing signal)
 2) It will be called from ir_signal_process_opt_sensor when we detect a screen update to 
    queue the next open signal.
    (below discusses how this will work)

 For scheduling the comparators we will just take the timer4 current value + the delay 
 (frame delay (for open signal) and frame duration (for close signal))

 For now we only need to support panasonic glasses for testing, later support all those inir_glasses_available.
*/
void ir_signal_schedule_send_request(ir_signal_type signal, uint16_t timer1_tcnt_target) {
  uint8_t scheduled_signal_index;
  const ir_signal_t* scheduled_signal_definition;

  ir_glasses_selected_library_sub_ir_signal_schedule_send_request = ir_glasses_selected_library;
  scheduled_signal_index = ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signal_index[signal];
  if (scheduled_signal_index != 255 && scheduled_signal_index < ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signal_count) {
    scheduled_signal_definition = &(ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signals[scheduled_signal_index]);
    if (scheduled_signal_definition->mode == 1) {
      timer1_tcnt_target -= scheduled_signal_definition->token_length;
    }
  }
  
  if (signal == SIGNAL_OPEN_LEFT || signal == SIGNAL_CLOSE_LEFT || signal == SIGNAL_OPEN_LEFT_CLOSE_RIGHT) {
    if (ir_signal_next_timer1_compa_signal == SIGNAL_NONE) {
      cli();
      ir_signal_next_timer1_compa_signal = signal;
      OCR1A = timer1_tcnt_target;
      bitSet(TIFR1, OCF1A);
      bitSet(TIMSK1, OCIE1A);
      sei();
    }
    else if (ir_signal_next_timer1_compa_next_signal == SIGNAL_NONE) {
      cli();
      ir_signal_next_timer1_compa_next_signal = signal;
      ir_signal_next_timer1_compa_next_time = timer1_tcnt_target;
      sei();
    }
  }
  else if ((signal == SIGNAL_OPEN_RIGHT || signal == SIGNAL_CLOSE_RIGHT || signal == SIGNAL_OPEN_RIGHT_CLOSE_LEFT)) {
    if (ir_signal_next_timer1_compb_signal == SIGNAL_NONE) {
      cli();
      ir_signal_next_timer1_compb_signal = signal;
      OCR1B = timer1_tcnt_target;    
      bitSet(TIFR1, OCF1B);
      bitSet(TIMSK1, OCIE1B);
      sei();
    }
    else if (ir_signal_next_timer1_compb_next_signal == SIGNAL_NONE) {
      cli();
      ir_signal_next_timer1_compb_next_signal = signal;
      ir_signal_next_timer1_compb_next_time = timer1_tcnt_target;
      sei();
    }
  }
  else if (ir_signal_next_timer1_compc_signal == SIGNAL_NONE) {
    cli();
    ir_signal_next_timer1_compc_signal = signal;
    OCR1C = timer1_tcnt_target;
    bitSet(TIFR1, OCF1C);
    bitSet(TIMSK1, OCIE1C);
    sei();
  }
}

ISR(TIMER1_COMPA_vect)
{
  ir_signal_type scheduled_signal = ir_signal_next_timer1_compa_signal;

  if (scheduled_signal == SIGNAL_OPEN_LEFT) {
    uint8_t scheduled_signal_index;
    const ir_signal_t* scheduled_signal_definition;
    uint16_t scheduled_signal_time_subtractor = 0;
    scheduled_signal_index = ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signal_index[scheduled_signal];
    if (scheduled_signal_index != 255 && scheduled_signal_index < ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signal_count) {
      scheduled_signal_definition = &(ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signals[scheduled_signal_index]);
      if (scheduled_signal_definition->mode == 1) {
        scheduled_signal_time_subtractor = scheduled_signal_definition->token_length;
      }
    }
    ir_signal_next_timer1_compa_signal = SIGNAL_CLOSE_LEFT;
    OCR1A += ((ir_frame_duration - scheduled_signal_time_subtractor) << 1);
  }
  else if (ir_signal_next_timer1_compa_next_signal != SIGNAL_NONE) {
    ir_signal_next_timer1_compa_signal = ir_signal_next_timer1_compa_next_signal;
    OCR1A = ir_signal_next_timer1_compa_next_time;
    ir_signal_next_timer1_compa_next_signal = SIGNAL_NONE;
    ir_signal_next_timer1_compa_next_time = 0;
  }
  else {
    ir_signal_next_timer1_compa_signal = SIGNAL_NONE;
    bitClear(TIMSK1, OCIE1A);
  }
  ir_signal_send_request(scheduled_signal);
}

ISR(TIMER1_COMPB_vect)
{
  ir_signal_type scheduled_signal = ir_signal_next_timer1_compb_signal;
  if (scheduled_signal == SIGNAL_OPEN_RIGHT) {
    uint8_t scheduled_signal_index;
    const ir_signal_t* scheduled_signal_definition;
    uint16_t scheduled_signal_time_subtractor = 0;
    scheduled_signal_index = ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signal_index[scheduled_signal];
    if (scheduled_signal_index != 255 && scheduled_signal_index < ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signal_count) {
      scheduled_signal_definition = &(ir_glasses_selected_library_sub_ir_signal_schedule_send_request->signals[scheduled_signal_index]);
      if (scheduled_signal_definition->mode == 1) {
        scheduled_signal_time_subtractor = scheduled_signal_definition->token_length;
      }
    }
    ir_signal_next_timer1_compb_signal = SIGNAL_CLOSE_RIGHT;
    OCR1B += ((ir_frame_duration - scheduled_signal_time_subtractor) << 1);
  }
  else if (ir_signal_next_timer1_compb_next_signal != SIGNAL_NONE) {
    ir_signal_next_timer1_compb_signal = ir_signal_next_timer1_compb_next_signal;
    OCR1B = ir_signal_next_timer1_compb_next_time;
    ir_signal_next_timer1_compb_next_signal = SIGNAL_NONE;
    ir_signal_next_timer1_compb_next_time = 0;
  }
  else {
    ir_signal_next_timer1_compb_signal = SIGNAL_NONE;
    bitClear(TIMSK1, OCIE1B);
  }
  ir_signal_send_request(scheduled_signal);
}

ISR(TIMER1_COMPC_vect)
{
  ir_signal_type scheduled_signal = ir_signal_next_timer1_compc_signal;
  ir_signal_next_timer1_compc_signal = SIGNAL_NONE;
  bitClear(TIMSK1, OCIE1C);
  ir_signal_send_request(scheduled_signal);
}

/*
 Responsible for converting external state change parameters into the those parameters used internally.
 Schedule the open signal for the current frames eye.
*/
void ir_signal_process_opt_sensor(uint8_t left_eye, bool duplicate) {
  ir_signal_type ir_desired_signal = (left_eye ^ ir_flip_eyes ? SIGNAL_OPEN_LEFT : SIGNAL_OPEN_RIGHT);
  uint8_t desired_signal_index;
  ir_glasses_selected_library = ir_glasses_available[ir_glasses_selected];
  desired_signal_index = ir_glasses_selected_library->signal_index[ir_desired_signal];
  if (desired_signal_index > ir_glasses_selected_library->signal_count || desired_signal_index == 255) {
    ir_desired_signal = (left_eye ^ ir_flip_eyes ? SIGNAL_OPEN_LEFT_CLOSE_RIGHT : SIGNAL_OPEN_RIGHT_CLOSE_LEFT);
    desired_signal_index = ir_glasses_selected_library->signal_index[ir_desired_signal];
    if (desired_signal_index > ir_glasses_selected_library->signal_count || desired_signal_index == 255) {
      return;
    }
  }
  cli();
  uint16_t current_tcnt1 = TCNT1;
  sei();
  ir_signal_schedule_send_request(ir_desired_signal, current_tcnt1 + (ir_frame_delay << 1));
}
