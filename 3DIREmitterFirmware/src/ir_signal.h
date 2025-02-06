/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */

#ifndef _IR_SIGNAL_H_
#define _IR_SIGNAL_H_

#define EYE_RIGHT 0
#define EYE_LEFT 1
#define SIGNAL_SEND_QUEUE_SIZE 4
#define MAX_SIGNALS_TO_GENERATE_WITHOUT_TRIGGER 160 // this must be larger than OPT_FRAMETIME_COUNT_PERIOD

#define IR_DRIVE_MODE_OPTICAL 0
#define IR_DRIVE_MODE_PC_SERIAL 1
#define IR_DRIVE_MODE_PC_SERIAL_LEFT 0
#define IR_DRIVE_MODE_PC_SERIAL_RIGHT 1

typedef enum
{
  SIGNAL_NONE,
  SIGNAL_OPEN_RIGHT,
  SIGNAL_CLOSE_RIGHT,
  SIGNAL_OPEN_LEFT,
  SIGNAL_CLOSE_LEFT,
  SIGNAL_OPEN_RIGHT_FAST_SWAP,
  SIGNAL_OPEN_LEFT_FAST_SWAP,
  SIGNAL_MODE_RIGHT_AND_LEFT,
  SIGNAL_MODE_RIGHT_ONLY,
  SIGNAL_MODE_LEFT_ONLY,
  SIGNAL_OPEN_RIGHT_CLOSE_LEFT,
  SIGNAL_OPEN_LEFT_CLOSE_RIGHT,
} ir_signal_type;

extern volatile uint8_t ir_drive_mode;
extern volatile uint8_t ir_glasses_selected;
extern volatile uint16_t ir_frame_duration;
extern volatile uint16_t ir_frame_delay;
extern volatile uint16_t ir_signal_spacing;
extern volatile uint8_t ir_average_timing_mode;
extern volatile uint8_t ir_flip_eyes;
extern volatile bool ir_led_token_active;
extern uint16_t target_frametime;

void ir_signal_init(void);
void ir_signal_send(ir_signal_type signal);
void ir_signal_send_request(ir_signal_type signal);
void ir_signal_send_finished(void);
void ir_signal_schedule_send_request(ir_signal_type signal, uint16_t delay);
void ir_signal_process_trigger(uint8_t left_eye, uint16_t frametime, int16_t ir_frame_delay_adjustment);

#endif /* _IR_SIGNAL_H_ */