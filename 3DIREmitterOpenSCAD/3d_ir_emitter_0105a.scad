/*
* Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
*/

/*
*
* 3D IR Emitter Mount
*
* Version 0101a: first attempt
* Version 0102a: lots of changes
* Version 0103a: added optional spacer for ir cut filter 10x10x0.55mm https://www.aliexpress.com/item/1005002502760553.html
* Version 0104a: revised ir cut filter to be on inside with no adhesive and minimal black backing
* Version 0105a: added alignment markers for calibration assistance mode
* 
* Todo:
*  - 
* 
* Notes:
*  - 
*
*/

ovr = 0.01;

// Screen bezel to pixel height dimension
// 11 mm - LG C1 OLED and Sony XBR-48A9S Bezel Only
// 7 mm - LG G3 OLED Bezel Only
// 14 mm - MMK 55MBL-EL Screen protector
// 9 mm - Sony X95K MiniLED
tv_top_bezel_to_pixel_wz = 11;

// Screen bezel thickness dimensions 
// 4.7 mm - LG C1 OLED Bezel Only (measured 4.4 mm)
// 5.5 mm - Sony XBR-48A9S Bezel Only
// 6.2 mm - LG C1 OLED with felt (back and front)
// 13.5 mm - LG G3 OLED Bezel Only
// 15.5 mm - LG G3 OLED Bezel Only with felt (back and front)
// 29 mm - MMK 55MBL-EL Screen protector
// 30 mm - MMK 55MBL-EL Screen protector with felt
// 32 mm - Sony X95K MiniLED (it has a rounded back so I've made it a little larger than what looks like 30mm any extra can be filled with spacers)
mm_r_wy = 6.2;

// Mount Ridge Ledge Height
// 10 mm - Most sets with a flat back that goes down > 10 mm from the top
// 20 mm - Sony X95K MiniLED (has a curved back for the first 10 mm)
mm_rl_wz = 10;

tv_top_wz = tv_top_bezel_to_pixel_wz+4.5; // we add 4.5 mm for optional faded board to help prevent potential burn-in

pcb_wx = 38; // measured 37.63
pcb_wz = 60; // measured 59.03
pcb_wy = 1.4;
pcb_wy_pkt = 3; // deep enough to hold the pcb board firmly but not soo deep as to hit the connector pins measured 3.4 with solder stubs sticking out
pcb_wb = 2; // plastic board thickness surrounding pcb
// pocket for solder stubs
pcb_p_px = 4;
pcb_p_wx = pcb_wx - 2*pcb_p_px;
pcb_p_wy = 2.4; // measured 4.0 minus 1.6 pcb depth
pcb_p_wz = 13; // height of pocket
pcb_p_sz = 1.5; // space between pocket and opt-101 top
// plastic back behind pcb that sticks above to screw into
pcb_b = false;
pcb_b_wy = 4; 
pcb_b_wz = pcb_wz + 2 * pcb_wb;
// plastic ridges on side to clip brace bracket onto
pcb_r = true;
pcb_r_wy = 1;
pcb_r_wx = 1;


// opt sensor (chip)
os_s_wx = 22.86; // measured 22.86 on pcbnew opt-101 center-to-center chip spacing
os_c_px_1 = 6.35; // measured 6.35 on pcbnew opt-101 left chip center from left edge
os_c_px_2 = 8.23; // measured 6.35 on pcbnew opt-101 left chip center from right edge
os_c_wx = 9.5; // measured 8 at top and 9 at bottom with solder bulge
os_c_wy = 4.3; // measured 4.5
os_c_wz = 10.5; // measured 10
os_c_pz_1 = 3; // measured 2.5 distance of opt sensor from bottom of pcb
os_c_pz_2 = pcb_wz - os_c_pz_1 - os_c_wz; // space below chip
os_c_pz_3 = (os_c_wz - 2.3) / 2; // photodiode is 2.3mm square (this is used to offset the photodiode to the edge of the screen for minimum obstruction)

// opt sensor ir cut filter mount
use_irf = false;
os_irf_s_wx = 6.0;
os_irf_s_wy = 0.9;
os_irf_s_wz = 6.0;
os_irf_s_rpx = (os_c_wx-os_irf_s_wx)/2;
os_irf_s_rpz = (os_c_wz-os_irf_s_wz)/2;
os_irf_wx = 10.5; // might need to be 11.0 depending on printer accuracy
os_irf_wy = 0.9;
os_irf_wz = 10.5; // might need to be 11.0 depending on printer accuracy
os_irf_rpx = (os_c_wx-os_irf_wx)/2;
os_irf_rpz = (os_c_wz-os_irf_wz)/2;

// mount top (ridge) (ridge ledge)

mm_wx = pcb_wx + 2*pcb_wb;
mm_wy = pcb_wy_pkt + os_c_wy + (use_irf ? os_irf_s_wy + os_irf_wy : 0);
mm_wz = tv_top_wz - os_c_pz_2 - os_c_pz_3 + pcb_wz + pcb_wb;
mm_r_px = 8;
mm_r_wx = mm_wx + 2*mm_r_px;
mm_r_wz = 2;
mm_rl_wy = 2;

// alignment markings
pcb_am = true;
pcb_am_wy = 3;
pcb_am_wxz = 2;
pcb_am3_px_off = os_c_px_1-os_c_px_2; // offset of center alignment marker to match center of opt sensors.

module 3d_player_tv_mount_main () {
  difference() {
    union() {
      translate([-mm_r_px, mm_wy+mm_r_wy, -mm_rl_wz])
      cube([mm_r_wx, mm_rl_wy, mm_rl_wz+ovr]);
      translate([-mm_r_px,0, 0])
      cube([mm_r_wx, mm_wy+mm_r_wy+mm_rl_wy, mm_r_wz]);
      translate([0,0,-mm_wz])
      cube([mm_wx, mm_wy, mm_wz+ovr]);
      if (pcb_b) {
        translate([0,0,-mm_wz])
        cube([mm_wx, pcb_b_wy, pcb_b_wz+ovr]);
      }
      if (pcb_r) {
        translate([-pcb_r_wx,0,-mm_wz])
        cube([pcb_wx+2*pcb_wb+2*pcb_r_wx, pcb_r_wy, mm_wz+ovr]);
      }
      if (pcb_am) {
        for (pxpz = [[0,os_c_pz_2+os_c_pz_3-tv_top_wz-pcb_wz+os_c_pz_1+os_c_wz/2], [pcb_wx+2*pcb_wb,os_c_pz_2+os_c_pz_3-tv_top_wz-pcb_wz+os_c_pz_1+os_c_wz/2], [(pcb_wx+2*pcb_wb+pcb_am3_px_off)/2,-mm_wz]]) {
          translate([pxpz[0],mm_wy-pcb_am_wy,pxpz[1]])
          rotate([0,45,0])
          translate([-pcb_am_wxz/2,0,-pcb_am_wxz/2])
          cube([pcb_am_wxz, pcb_am_wy, pcb_am_wxz]);
        }
      }
    }
    union() {
      echo(os_c_pz_1+os_c_wz+2);
      translate([pcb_wb, -ovr, os_c_pz_2 + os_c_pz_3 - tv_top_wz - pcb_wz])
      cube([pcb_wx,pcb_wy_pkt+2*ovr,pcb_wz]);
      translate([pcb_wb+pcb_p_px, pcb_wy_pkt-ovr, os_c_pz_2 + os_c_pz_3 - tv_top_wz - pcb_wz + os_c_pz_1+os_c_wz+pcb_p_sz ])
      cube([pcb_p_wx,pcb_p_wy+ovr,pcb_p_wz]);
      translate([0, -ovr, os_c_pz_2 + os_c_pz_3 - tv_top_wz - pcb_wz])
      union() {
        for (px = [pcb_wb+os_c_px_1-os_c_wx/2, pcb_wb+pcb_wx-os_c_px_2-os_c_wx/2]) {
          if (use_irf) {
            translate([px-(os_irf_wx-os_c_wx)/2,pcb_wy_pkt,os_c_pz_1-(os_irf_wz-os_c_wz)/2])
            cube([os_irf_wx,os_c_wy+os_irf_wy+2*ovr,os_irf_wz]); // opt101 hole
            translate([px+os_irf_s_rpx,pcb_wy_pkt+os_c_wy+os_irf_wy,os_c_pz_1+os_irf_s_rpz])
            cube([os_irf_s_wx,os_irf_s_wy+2*ovr,os_irf_s_wz]); // opt101 hole above chip
          }
          else {
            translate([px,pcb_wy_pkt,os_c_pz_1])
            cube([os_c_wx,os_c_wy+2*ovr,os_c_wz]); // opt101 hole
          }
        }
      }
    }
  }
}

mb_wc = 1.0; // width of clip needs to bend slightly
mb_tf = 0.8; // tension factor on ridges
mb_wx = mm_wx + 2 * mb_tf * pcb_r_wx + 2 * mb_wc;
mb_wz = 13+pcb_wb; // measured 11.0
mb_px = - mb_tf * pcb_r_wx - mb_wc;
mb_c_wy = 3.5; // clip depth
mb_c_wt = 0.4; // tolerances on clip to mating side
mb_c_wt_s = 0.2; // tolerances on clip gripping part
mb_rb_wx = 7; // reset button
mb_rb_wz = 7; // reset button
mb_rb_pz = 7.5; // measured 6.5

module 3d_player_tv_mount_bracket () {
  difference() {
    union() {
      translate([mb_px-mb_c_wt,-mb_wc-mb_c_wt,-mm_wz+pcb_wb])
      cube([mb_wx+2*mb_c_wt, mb_c_wy+2*mb_c_wt, mb_wz]);
    }
    union() {
      translate([0,0,-mm_wz-ovr])
      cube([mm_wx+2*mb_c_wt_s, mm_wy, mm_wz+2*ovr]);
      translate([-pcb_r_wx-mb_c_wt,-mb_c_wt,-mm_wz-ovr])
      cube([pcb_wx+2*pcb_wb+2*pcb_r_wx+2*mb_c_wt, pcb_r_wy+2*mb_c_wt, mm_wz+2*ovr]);
      translate([pcb_wx/2+pcb_wb-mb_rb_wx/2, -mb_wc-mb_c_wt-ovr, -mm_wz+mb_rb_pz-mb_rb_wz/2+pcb_wb])
      cube([mb_rb_wx, mb_wc+2*ovr, mb_rb_wz]);
    }
  }
}


translate([0, mm_r_wy+20, mm_r_wz])
rotate([180,0,0])
3d_player_tv_mount_main();
translate([0, 0, mb_wz-mm_wz+pcb_wb])
rotate([180,0,0])
3d_player_tv_mount_bracket();
