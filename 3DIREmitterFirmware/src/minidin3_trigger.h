/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */

#ifndef _MINIDIN3_TRIGGER_H_
#define _MINIDIN3_TRIGGER_H_

// D10
// Stereo Sync Signal: (1) Standard TTL levels (5V and 0V). Logic 1 state (high) is valid when the signal level is higher than 2.4V and Logic 0 state (low) is valid when the signal level is lower than 0.8V. (2) The host shall not be required to sink more than 10mA in the Logic 0 state nor source more than 0.5mA in the Logic 1 state. (3) Logic 1 state corresponds to the display of the left-eye image and Logic 0 state corresponds to the display of the right-eye image. (4) The signal shall be a square wave with a nominal duty cycle of 50%. The transition from state to state shall occur within 3 horizontal lines of the start of the vertical sync pulse (but not before the start of vertical blanking).
#define MINIDIN3_3D_STEREO_SYNC_LEFT_OPEN_D10 6
#define DDR_MINIDIN3_3D_STEREO_SYNC_LEFT_OPEN_D10 DDRB
#define PORT_MINIDIN3_3D_STEREO_SYNC_LEFT_OPEN_D10 PORTB
#define PIN_MINIDIN3_3D_STEREO_SYNC_LEFT_OPEN_D10 PINB

void minidin3_trigger_init(void);
void minidin3_trigger_stop(void);
void minidin3_trigger_settings_changed(void);
void minidin3_trigger_update(void);

#endif /* _MINIDIN3_TRIGGER_H_ */