/*
* Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
*/

/*
*
* 3D MiniDIN3, RF, DLPLink Relay Case
*
* Version 0203a: support for dlplink opt101 board
* Version 0201a: support for din3 to ir relay
* Version 0101a: support for rf to ir relay
* Todo:
*  - 
* 
* Notes:
*  - 
*
*/

include_dlplink_sensor = true;
include_eye_swap_button = true;
include_minidin3_cable_hole = true;

/* [Hidden:] */

$fn = 32;
ovr = 0.01;
big = 10;

bevel_d = 1.0;

mb_base_d = 2.5; // depth (needs to provide clearance for m1.4 4mm screws minus pcb depth)
main_pcb_wh = 20.0; // components and pcb // measured 17.6
mc_usbh_pz = 15;

main_pcb_px = 3;
base_wx = 61;
base_wy = 38;
base_wz = 3;
base_ww = 2; // wall width
base_wh = 10; // wall height
base_fww = 3; // front wall width
base_fwh = 29; // front wall height
base_bww = base_fww; // back wall width
base_bwh = base_fwh; // back wall height
rows_of_leds_populated = 2;
base_irh_wy = 17.5; // ir hole
base_irh_wz = (rows_of_leds_populated == 2 ? 11 : (rows_of_leds_populated == 1 ? 5 : 0));
base_irh_py = (base_wy - base_irh_wy) / 2;
base_irh_pz = 5;
base_irs_py = base_irh_py - 6; // 2.5 or 6 depending on side
base_irs_pz = base_irh_pz - 7;
base_irm_wx = 2; // ir mount
base_irm12_wy = 4;
base_irm12_wz = 24;
base_irm3_wy = 6;
base_irm3_wz = 6;
base_irm13_py = base_irs_py + 3 - base_irm12_wy;
base_irm2_py = base_irs_py + 26 - 4;
base_irm12_pz = base_irs_pz;
base_irm3_pz = base_irs_pz + 24 - base_irm3_wz;
base_usbh_wy = 13; // usb hole
base_usbh_wz = main_pcb_wh+mb_base_d-mc_usbh_pz+4;
base_usbh_py = 6;
base_usbh_pz = 13;
base_mbm_wz = 6; // main board mount
base_mbm1_wx = 8;
base_mbm1_wy = 37;
base_mbm1_px = 13+main_pcb_px;
base_mbm1_py = 3;
base_mbm2_wx = 43;
base_mbm2_wy = 10;
base_mbm2_px = base_mbm1_px;
base_mbm2_py = base_mbm1_py+base_mbm1_wy-base_mbm2_wy;
base_obm_px = 35;
base_obm_wx = 10;
base_obm_pdz = 6;
base_obma_wz = 3;
base_obma_wy = 8;
base_obmr_pdz = 3;

m1_4_wd_h_st = 1.3; // m1.4 self threading hole diameter
base_smh_list = [[2.5,21],[23.5,21]]; // y, z
main_pcb_wx = 37.5;
main_pcb_wy = 50;
main_pcb_py = 3.5;
base_mmh_list = [[34,main_pcb_wy-3.5+main_pcb_py+main_pcb_px],[6.5,main_pcb_wy-37.5+main_pcb_py+main_pcb_px]]; // y, x

base_obmmh_px = base_obm_px+base_obm_wx/2;
base_obmmh_py = base_mmh_list[0][0];
base_obmh_wx = 12;
base_obmh_wy = 12;
base_obmh_px = base_obmmh_px+8;
base_obmh_py = base_obmmh_py-base_obmh_wy+3.5;
base_md3d_wd_h = 3.1;
base_md3d_py = 13;

cover_ww = 2;
cover_tol = 0.5;
cover_tab_wx = 5;
cover_tab_wy = 1.5;
cover_tab_wz = 2;
cover_esb_wd = 5;
cover_esbh_wd = cover_esb_wd+1.5;
cover_esbh_px = 27;
cover_esbh_py = base_wy-9;
cover_esbhi_wd = 3.5;
cover_esbo_wd = cover_esb_wd+2; // diameter of portion under case with lip to stop button falling out
cover_esbhi_wz = 5; // height of walls that surround inside button
cover_esbs_wz = 0.1; // height difference between top of inside and outside button
cover_esbt_wz = cover_ww+2; // height of top of button

module base() {
  difference() {
    union() {
      cube([base_wx,base_wy,base_wz]); // base
      translate([-base_fww,-base_ww,0])cube([base_fww,base_wy+2*base_ww,base_fwh+base_wz]); // front
      translate([base_wx,-base_ww,0])cube([base_bww,base_wy+2*base_ww,base_bwh+base_wz]); // back
      translate([-base_fww,-base_ww,0])cube([base_wx+base_ww+base_fww,base_ww,base_wh+base_wz]); // right
      translate([-base_fww,base_wy,0])cube([base_wx+base_ww+base_fww,base_ww,base_wh+base_wz]); // left
      translate([-ovr,base_irm13_py,base_irm12_pz+base_wz+base_mbm_wz])cube([base_irm_wx+ovr,base_irm12_wy,base_irm12_wz]); // ir mount 1
      translate([-ovr,base_irm2_py,base_irm12_pz+base_wz+base_mbm_wz])cube([base_irm_wx+ovr,base_irm12_wy,base_irm12_wz]); // ir mount 2
      translate([-ovr,base_irm13_py,base_irm3_pz+base_wz+base_mbm_wz])cube([base_irm_wx+ovr,base_irm3_wy,base_irm3_wz]); // ir mount 3
      translate([base_mbm1_px,base_mbm1_py,base_wz-ovr])cube([base_mbm1_wx,base_mbm1_wy,base_mbm_wz]);  // main board mount
      translate([base_mbm2_px,base_mbm2_py,base_wz-ovr])cube([base_mbm2_wx,base_mbm2_wy,base_mbm_wz]);  // main board mount
    if (include_dlplink_sensor) {
      translate([base_obm_px,base_wy,0])cube([base_obm_wx,base_ww,base_bwh+base_wz-base_obm_pdz-base_obma_wz+ovr]); // opt board mount tower
        translate([base_obm_px,base_wy+base_ww-base_obma_wy,base_bwh+base_wz-base_obm_pdz-base_obma_wz])cube([base_obm_wx,base_obma_wy+ovr,base_obma_wz]);
   // opt board mount arm
        // opt board mount ramp
        hull() {
          translate([base_obm_px,base_wy,base_bwh+base_wz-base_obm_pdz-base_obmr_pdz-base_obma_wz+ovr])cube([base_obm_wx,base_ww,ovr]);
          translate([base_obm_px,base_wy+base_ww-base_obma_wy,base_bwh+base_wz-base_obm_pdz-base_obma_wz])cube([base_obm_wx,base_obma_wy+ovr,ovr]); 
        }
      }
       
    }
    union() {
      translate([-base_fww-ovr,base_irh_py,base_irh_pz+base_wz+base_mbm_wz])cube([base_fww+base_irm_wx+2*ovr,base_irh_wy,base_irh_wz]);
      translate([base_wx-ovr,base_usbh_py,base_usbh_pz+base_wz+base_mbm_wz])cube([base_bww+2*ovr,base_usbh_wy,base_usbh_wz]);
      
      for (ss=base_smh_list) {
        translate([0,base_irs_py+ss[0],base_irs_pz+base_wz+base_mbm_wz+ss[1]])rotate([0,90,0])cylinder(h=base_irm_wx+ovr,d=m1_4_wd_h_st);
      }
      
      for (ss=base_mmh_list) {
        translate([ss[1],ss[0],base_wz])cylinder(h=10+base_mbm_wz+ovr,d=m1_4_wd_h_st);
      }
      
      if (include_dlplink_sensor) {
        translate([base_obmmh_px,base_obmmh_py,base_bwh+base_wz-base_obm_pdz-base_obmr_pdz-base_obma_wz-ovr])cylinder(h=base_obm_pdz+base_obmr_pdz+2*ovr,d=m1_4_wd_h_st); // opt board mount screw hole
      }
      if (include_minidin3_cable_hole) {
        translate([base_wx-ovr,base_md3d_py,base_wz+base_md3d_wd_h/2])rotate([0,90,0])cylinder(h=base_bww+2*ovr,d=base_md3d_wd_h);// minidin 3d sync out cable hole
      }
      
      translate([base_wx/2-cover_tab_wx/2-cover_tol,-base_ww-ovr,-ovr])cube([cover_tab_wx+2*cover_tol,cover_tab_wy+cover_tol+ovr,cover_tab_wz+cover_tol+ovr]); // right lock tab
      translate([base_wx/2-cover_tab_wx/2-cover_tol,base_wy+base_ww-cover_tab_wy-cover_tol,-ovr])cube([cover_tab_wx+2*cover_tol,cover_tab_wy+cover_tol+ovr,cover_tab_wz+cover_tol+ovr]); // left lock tab
    }
  }
}

module cover() {
  difference() {
    union() {
      translate([-base_fww,-base_ww-cover_tol-ovr,base_wz+base_fwh])cube([base_wx+base_bww+base_fww,base_wy+2*base_ww+2*cover_tol+2*ovr,cover_ww]); // top
      translate([-base_fww,-base_ww-cover_ww-cover_tol,0])cube([base_wx+base_bww+base_fww,cover_ww,base_wz+base_fwh+cover_ww]); // right
      translate([-base_fww,base_wy+base_ww+cover_tol,0])cube([base_wx+base_bww+base_fww,cover_ww,base_wz+base_fwh+cover_ww]); // left
      translate([base_wx/2-cover_tab_wx/2,-base_ww-cover_tol,0])cube([cover_tab_wx,cover_tab_wy,cover_tab_wz]); // right lock tab
      translate([base_wx/2-cover_tab_wx/2,base_wy+base_ww+cover_tol-cover_tab_wy,0])cube([cover_tab_wx,cover_tab_wy,cover_tab_wz]); // left lock tab
    }
    union() {
      if (include_dlplink_sensor) {
        translate([base_obmh_px,base_obmh_py,base_wz+base_fwh-ovr])cube([base_obmh_wx,base_obmh_wy,cover_ww+2*ovr]); // hole for dlplink optical sensor in case top, comment this line out if you don't need it
      }
      if (include_eye_swap_button) {
        translate([cover_esbh_px,cover_esbh_py,base_wz+base_fwh-ovr])cylinder(h=cover_ww+2*ovr,d=cover_esbh_wd); // hole for eye swap button on switch 4 in case top, comment this line out if you don't need it
      }
    }
  }
}

// SMD Switch used is 6x6x19 4Pin Tactile Tact Push Button Micro Switch Self-reset Switch
// https://www.aliexpress.com/item/1005005845072975.html
module button() {
  difference() {  
    union() {
      cylinder(h=cover_esbhi_wz+cover_esbs_wz,d=cover_esbo_wd); // button base
      translate([0,0,cover_esbhi_wz+cover_esbs_wz-ovr])cylinder(h=cover_esbt_wz+ovr,d=cover_esb_wd); // button top
    }
    union() {
      translate([0,0,-ovr])cylinder(h=cover_esbhi_wz+ovr,d=cover_esbhi_wd); // inside pocket for sitting on button
    }
  }
}

translate([0,10,0])
base();
translate([0,-10,base_wz+base_fwh+cover_ww])
rotate([180,0,0])
cover();
if (include_eye_swap_button) {
  translate([0,60,0])
  button();
}