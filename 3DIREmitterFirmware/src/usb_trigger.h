/*
 * Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
 */

#ifndef _USB_TRIGGER_H_
#define _USB_TRIGGER_H_

#define USB_FRAMETIME_COUNT_PERIOD_2PN 7 // This is how often we update the frametime in cycles as 2^(USB_FRAMETIME_COUNT_PERIOD_2PN) (eg 2^7 = 128)
#define USB_FRAMETIME_COUNT_PERIOD (1 << USB_FRAMETIME_COUNT_PERIOD_2PN)

#include <stdint.h>

void usb_trigger_Init(void);
void usb_trigger_SettingsChanged(void);
void usb_trigger_Update(uint8_t left_eye);

#endif /* _USB_TRIGGER_H_ */