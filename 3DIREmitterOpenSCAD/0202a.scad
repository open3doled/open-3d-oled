/*
* Open3DOLED is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
*/

/*
*
* 3D IR Emitter Mount V2.2
*
* Version 0202a: first attempt
* Todo:
*  - 
* 
* Notes:
*  - 
*
*/

/* [TV Settings:] */

// Screen bezel to pixel height dimension (lgc155=11)
tv_bezel_to_pixels_vertical_distance = 24;
/*
  13.5 mm - LG G1 OLED 77
  15 mm - LG CX OLED Bezel Only
  13 mm - LG C1 OLED 83
  11 mm - LG C1 OLED 55 and Sony XBR-48A9S Bezel Only
  14 mm - LG C1 OLED 55 and MMK 55MBL-EL Screen protector
  9 mm - LG C2 or C3
  7 mm - LG G3 OLED Bezel Only
  9 mm - Sony X95K MiniLED
  10 mm - Sony X90CL MiniLED
  14 mm - Sony XR-77A80J
  6.5 mm - Viewsonic XG2431
  16 mm - Hisense 100U7K (used 20mm)
  13 mm - TCL 98QM751G (used 15mm)
*/

// Screen bezel thickness dimension (lgc155=4.7)
tv_bezel_thickness = 63;
/*
  ** add 1.5 mm for felt and tolerance **
  25.1 mm - LG G1 OLED 77
  8 mm - LG CX OLED Bezel Only (measure 8 mm)
  4.7 mm - LG C1 OLED 83 Bezel Only (measured 6.35 mm)
  4.7 mm - LG C1 OLED 55 Bezel Only (measured 4.4 mm)
  29 mm - LG C1 OLED 55 and MMK 55MBL-EL Screen protector
  6.2 mm - LG C2 or C3 Bezel Only
  5.5 mm - Sony XBR-48A9S Bezel Only
  13.5 mm - LG G3 OLED Bezel Only
  32 mm - Sony X95K MiniLED (it has a rounded back so I've made it a little larger than what looks like 30mm any extra can be filled with spacers)
  32 mm - Sony X95CL MiniLED (it has a rounded back so I've made it a little larger than what looks like 30mm any extra can be filled with spacers)
  29 mm - Viewsonic XG2431 (it has a rounded back so we just use the thickest measurement and you will need adhesive on the top bezel.)
  58 mm - Hisense 100U7K (used 63mm)
  44 mm - TCL 98QM751G (used 47mm)
  
*/

/* [Case Settings:] */

// This is the wall thickness for the case
bevel_w = 1.0; 

// Rows of ledss populated (starting from bottom row)
rows_of_leds_populated = 1;

// thickness of ir led acrylic window sheet
ir_led_window_plastic_thickness = 0;

/* [STL Print Settings:] */
// Orientate modules for ease of printing
orientate_print_ready = "no"; // [yes,no]

/* [PCB Diode Settings:] */

// The vertical position of the photodiode on the sensor pcb (opt101=18, bpw34=21)
sensor_pcb_sensor_vertical_position = 21.0; // bpw34 // measured from top
// sensor_pcb_sensor_vertical_position = 18; // opt101 // measured from top

// This is the width of photosensitive area (6)
photodiode_die_width = 6.0; // actual width is 3 mm but we use a larger value to get more light

// This is how far the photodiode stands of the PCB (opt101=4.3, bpw34=1.8)
photodiode_depth = 1.8; // bpw34  // measured 1.6
// photodiode_depth = 4.3; // opt101

/* [Explode Design Vertically:] */
explode=35;   // [0, 0.5, 35]


/* [Hidden:] */

shift_required = sensor_pcb_sensor_vertical_position - photodiode_die_width / 2 - tv_bezel_to_pixels_vertical_distance;

$fn = 32;
ovr = 0.01;
big = 10;

bevel_d = 1.0;

m1_4_wd_h_st = 1.3; // m1.4 self threading hole diameter
m1_4_wd_h_ch = 1.7;  // m1.4 clear hole diameter  // measured 1.4
m1_4_wd_h_hch = 3.0; // m1.4 head clear hole diameter // measured 2.5 (good to have 3 for the screw driver)


  
main_pcb_wx = 37.5;
main_pcb_wy = 50;
mb_base_er_wx = 1.0;
mb_base_er_wy = 3.0;
mb_base_er_wz = 3.0;
mb_base_w_ox = 2.0+mb_base_er_wx; // mb_base_er_wx mm of this will be for ridges on the sides to stop bending
mb_base_w_oy = 2.0+max(4.0,mb_base_er_wy); // the pro micro pcb needs an extra 4mm of clearance due to overhang.
mb_base_wx_o = main_pcb_wx+2*mb_base_w_ox;
mb_base_wy_o = main_pcb_wy+mb_base_w_oy;
mb_base_w_i = 2.0;
mb_base_wx_i = main_pcb_wx-2*mb_base_w_i;
mb_base_wy_i = main_pcb_wy-mb_base_w_i;
mb_base_bw = 0.8; // backwall
mb_base_d = 2.5; // depth (needs to provide clearance for m1.4 4mm screws minus pcb depth)
mmh_wz = 3; // mount hole
mmh_wr_s = 2.5;
mmh_wr_h = m1_4_wd_h_st/2;
mmh_list = [[34,3.5],[6.5,37.5]];
mbh_wr_h = m1_4_wd_h_st/2; // bottom hole
mt_base_wx_o = main_pcb_wx+2*mb_base_w_ox; // top
mt_base_d = 2;
mt_base_d_eff = mt_base_d+(shift_required > 0 ? shift_required : 0);
mt_base_wz = tv_bezel_thickness+mb_base_d;

sensor_pcb_wx = 26;
sensor_pcb_wy = 23.5;
sensor_pcb_wy_eff = sensor_pcb_wy+(shift_required < 0 ? -shift_required : 0);
sb_base_w_ox = 2.0;
sb_base_w_oy = 2.0;
sb_base_wx_o = sensor_pcb_wx+2*sb_base_w_ox;
sb_base_wy_o = sensor_pcb_wy_eff+sb_base_w_oy;
sb_base_w_i = 0.0;
sb_base_wx_i = sensor_pcb_wx-2*sb_base_w_i;
sb_base_wy_i = sensor_pcb_wy-sb_base_w_i;
sb_base_bw = 0.8; // backwall
sb_base_d = max(2.5, photodiode_depth+sb_base_bw); // depth - needs to be high enough to create a tunnel to reduce sensor crosstalk (and clearance for m1.4 4mm screws minus pcb depth)
ssh_wxy = 5; // sensor hole
ssh_px = [5.5, 20.5];
ssh_py = sensor_pcb_wy-sensor_pcb_sensor_vertical_position+sb_base_w_oy+bevel_w;
sdb_px = 13; // sensor divider bar
sdb_wx = 2;
sdb_wy = 12;
smh_wz = sb_base_d;  // mount hole
smh_wr_s = 2.5;
smh_wr_h = m1_4_wd_h_st/2;
smh_list = [[2.5,21],[23.5,21]];
st_base_wx_o = sensor_pcb_wx+2*sb_base_w_ox; // top
st_base_d = 2;
st_base_wz = sb_base_d;

sensor_o_x = (main_pcb_wx-sensor_pcb_wx+2*mb_base_w_ox-2*sb_base_w_ox)/2;
sensor_o_y = main_pcb_wy+mb_base_w_oy-sensor_pcb_wy_eff-sb_base_w_oy+(shift_required > 0 ? shift_required : 0);
sensor_o_z = -tv_bezel_thickness;

module base() {

  // main board
  translate([0,0,0])
  union() {
    difference() {
      union() {
        // main
        // bevel base
        translate([-mb_base_wx_o/2-bevel_w,0,0])
        cube([mb_base_wx_o+2*bevel_w,mb_base_wy_o+bevel_w,bevel_d]);
        // base
        translate([-mb_base_wx_o/2,bevel_w,0])
        cube([mb_base_wx_o,mb_base_wy_o,mb_base_d]);
        // top
        translate([-mt_base_wx_o/2,mb_base_wy_o+bevel_w-ovr,mb_base_d-mt_base_wz])
        cube([mt_base_wx_o,mt_base_d_eff+ovr,mt_base_wz]);
        // edge ridges
        for (px=[-mb_base_wx_o/2,mb_base_wx_o/2-mb_base_er_wx]) {
          translate([px,bevel_w,mb_base_d-ovr])
          cube([mb_base_er_wx,mb_base_wy_o,mb_base_er_wz+ovr]);
          translate([px+mb_base_er_wx,bevel_w+mb_base_wy_o,mb_base_d-ovr])
          rotate([0,-90,0])
          linear_extrude(mb_base_er_wx)
          polygon([[-ovr,-ovr],[-ovr,mt_base_d_eff],[mb_base_er_wz,-ovr]]);
        }
        translate([-mb_base_wx_o/2,bevel_w,mb_base_d-ovr])
        cube([mb_base_wx_o,mb_base_er_wy,mb_base_er_wz+ovr]);
      }
      union() {
        // pcb cutaway
        translate([-mb_base_wx_i/2,mb_base_w_oy+bevel_w+mb_base_w_i,mb_base_bw])
        cube([mb_base_wx_i,mb_base_wy_i,mb_base_d-
  mb_base_bw+ovr]);
        // bottom hole
        translate([0,bevel_w-ovr,mb_base_d+mb_base_er_wz/2])
        rotate([-90,0,0])
        cylinder(h=mb_base_er_wy+2*ovr,r=mbh_wr_h);
      }
    }
    difference() {
      union() {
        // mounting hole standoff
        for (h=mmh_list) {
          translate([h[0]-main_pcb_wx/2,h[1]+mb_base_w_oy+bevel_w,0])
          cylinder(h=mmh_wz, r=mmh_wr_s);
        }
        translate([-main_pcb_wx/2,mmh_list[1][1]+mb_base_w_oy+bevel_w-mmh_wr_s,0])
        cube([mmh_list[1][0],2*mmh_wr_s,mmh_wz]);
      }
      union() {
        for (h=mmh_list) {
          // mounting hole
          translate([h[0]-main_pcb_wx/2,h[1]+mb_base_w_oy+bevel_w,-ovr])
          cylinder(h=mmh_wz+2*ovr, r=mmh_wr_h);
        }
      }
    }
  }
    
  // sensor board
  translate([sensor_o_x,sensor_o_y,sensor_o_z])
  rotate([0,180,0])
  union() {
    difference() {
      union() {
        // main
        // bevel base
        translate([-sb_base_wx_o/2-bevel_w,0,0])
        cube([sb_base_wx_o+2*bevel_w,sb_base_wy_o+bevel_w,bevel_d]);
        // base
        translate([-sb_base_wx_o/2,bevel_w,0])
        cube([sb_base_wx_o,sb_base_wy_o,sb_base_d]);
        // top
        translate([-st_base_wx_o/2,sb_base_wy_o+bevel_w-ovr,-ovr])
        cube([st_base_wx_o,st_base_d+ovr,st_base_wz+ovr]);
      }
      // pcb cutaway
      union() {
        translate([-sb_base_wx_i/2,sb_base_w_oy+bevel_w+sb_base_w_i,sb_base_bw])
        cube([sb_base_wx_i,sb_base_wy_i,sb_base_d-
  sb_base_bw+ovr]);
      }
      // photodiode cutaways
      union() {
        for (x=ssh_px) {
          translate([x-sensor_pcb_wx/2-ssh_wxy/2, ssh_py-ssh_wxy/2,-ovr])
          cube([ssh_wxy,ssh_wxy,sb_base_d+2*ovr]);
        }
      }
    }
    difference() {
      union() {
        // mounting hole standoff
        for (h=smh_list) {
          translate([h[0]-sensor_pcb_wx/2,h[1]+sb_base_w_oy+bevel_w,0])
          cylinder(h=smh_wz, r=smh_wr_s);
        }
        /*
        translate([-sensor_pcb_wx/2+smh_list[0][0]-smh_wr_s,sb_base_w_oy+bevel_w,0])
        cube([2*smh_wr_s,smh_list[0][1],smh_wz]);
        */
        translate([-sensor_pcb_wx/2,smh_list[0][1]+sb_base_w_oy+bevel_w-smh_wr_s,0])
        cube([smh_list[0][0],2*smh_wr_s,smh_wz]);
        translate([sensor_pcb_wx/2-smh_list[0][0],smh_list[0][1]+sb_base_w_oy+bevel_w-smh_wr_s,0])
        cube([smh_list[0][0],2*smh_wr_s,smh_wz]);
        translate([-sensor_pcb_wx/2+sdb_px-sdb_wx/2,sb_base_w_oy+bevel_w,0])
        cube([sdb_wx,sdb_wy,smh_wz]);
      }
      union() {
        for (h=smh_list) {
          // mounting hole
          translate([h[0]-sensor_pcb_wx/2,h[1]+sb_base_w_oy+bevel_w,-ovr])
          cylinder(h=smh_wz+2*ovr, r=smh_wr_h);
        }
      }
    }
  }
}

cover_tol = 0.3; // this is how much tolerance to allow between the cover and the bevel inner edge.
cover_screw_vertical_pos = 1;

mc_mh_wr_s = 2;
mc_mh_wr_h_ch = m1_4_wd_h_ch/2;
mc_mh_wr_h_hch = m1_4_wd_h_hch/2;
mc_mh_wr_st = mc_mh_wr_h_hch+1; // 1 gives a double wall
mc_bh_wr_h_ch = m1_4_wd_h_ch/2;
//cover_channel_width = mc_mh_wr_s+mc_mh_wr_st-bevel_w+0.5; // cable channel and securing screw mount
cover_channel_width = 2*mc_mh_wr_s-bevel_w+0.5; // cable channel and securing screw mount

main_pcb_wh = 20.0; // components and pcb // measured 17.6
mc_cc_wy = cover_channel_width;
mc_p1_px = mb_base_wx_o/2-sb_base_wx_o;
mc_usbh_px = 6; // should be 7 but appears to actually be 6
mc_usbh_pz = 15;
mc_usbh_wx = 13;
mc_usbh_wz = main_pcb_wh+mb_base_d-mc_usbh_pz;
mc_ts_wx = 1.2;
mc_ts_wy = 4;
mc_mh_pz_st = 5;
mc_mh_pxl = [main_pcb_wx/2-sensor_pcb_wx*0.05+mb_base_w_ox-sb_base_w_ox,main_pcb_wx/2-sensor_pcb_wx*0.95+mb_base_w_ox-sb_base_w_ox];
mc_mh_py = mb_base_wy_o+mt_base_d_eff+mc_cc_wy+2*bevel_w-mc_mh_wr_s;



module cover_main() {
  union () {
    difference() {
      union() {
        // main cover p1
        translate([mc_p1_px-bevel_w,0,0])
        cube([sb_base_wx_o+2*bevel_w,mb_base_wy_o+mt_base_d_eff+mc_cc_wy+2*bevel_w,main_pcb_wh+mb_base_d+bevel_w]);
        // main cover p2
        translate([-mb_base_wx_o/2-bevel_w,0,0])
        cube([mb_base_wx_o+2*bevel_w,mb_base_wy_o+mt_base_d_eff+2*bevel_w,main_pcb_wh+mb_base_d+bevel_w]);
      }
      union() {
        // main cutaway p1
        translate([mc_p1_px-cover_tol,bevel_w-cover_tol,-ovr])
        cube([sb_base_wx_o+2*cover_tol,mb_base_wy_o+2*cover_tol+mt_base_d_eff+mc_cc_wy,main_pcb_wh+mb_base_d]);
        // main cutaway p2
        translate([-mb_base_wx_o/2-cover_tol,bevel_w-cover_tol,-ovr])
        cube([mb_base_wx_o+2*cover_tol,mb_base_wy_o+2*cover_tol+mt_base_d_eff,main_pcb_wh+mb_base_d]);
        // secondary cutaway
        translate([-mb_base_wx_o/2-bevel_w-2*ovr,-ovr,-ovr])
        cube([mb_base_wx_o+2*bevel_w+4*ovr,mb_base_wy_o+bevel_w+cover_tol+ovr,bevel_d+cover_tol+ovr]);
        // usb cutaway
        translate([-main_pcb_wx/2+mc_usbh_px,-ovr,mc_usbh_pz-ovr])
        cube([mc_usbh_wx,bevel_w+2*ovr,mc_usbh_wz]);
        for (mc_mh_px=mc_mh_pxl) {
          // mounting hole
          translate([mc_mh_px,mc_mh_py,-ovr])
          cylinder(h=main_pcb_wh+mb_base_d+bevel_w+2*ovr,r=mc_mh_wr_h_ch);
          // mounting hole top
          translate([mc_mh_px,mc_mh_py,mc_mh_pz_st+bevel_w])
          cylinder(h=main_pcb_wh+mb_base_d-mc_mh_pz_st+bevel_w+ovr,r=mc_mh_wr_h_hch);
          translate([mc_mh_px-mc_mh_wr_h_hch,mc_mh_py,mc_mh_pz_st+bevel_w])
          cube([2*mc_mh_wr_h_hch,mc_mh_wr_h_hch+big,main_pcb_wh+mb_base_d-mc_mh_pz_st+bevel_w]);
        }
        // bottom hole
        translate([0,-ovr,mb_base_d+mb_base_er_wz/2])
        rotate([-90,0,0])
        cylinder(h=bevel_w+2*ovr,r=mc_bh_wr_h_ch);
      }
    }
    difference() {
      intersection() {
        union() {
          for (mc_mh_px=mc_mh_pxl) {
            // mounting hole standoff
            translate([mc_mh_px,mc_mh_py,0])
            cylinder(h=main_pcb_wh+mb_base_d,r=mc_mh_wr_s);
            translate([mc_mh_px-mc_mh_wr_s,mc_mh_py,0])
            cube([2*mc_mh_wr_s,mb_base_wy_o+mt_base_d_eff+mc_cc_wy+2*bevel_w-mc_mh_py,main_pcb_wh+mb_base_d]);
            // mounting hole standoff top
            translate([mc_mh_px,mc_mh_py,mc_mh_pz_st])
            cylinder(h=main_pcb_wh+mb_base_d-mc_mh_pz_st+bevel_w,r=mc_mh_wr_st);
            translate([mc_mh_px-mc_mh_wr_st,mc_mh_py,mc_mh_pz_st])
            cube([2*mc_mh_wr_st,mb_base_wy_o+mt_base_d_eff+mc_cc_wy+2*bevel_w-mc_mh_py,main_pcb_wh+mb_base_d-mc_mh_pz_st+bevel_w]);
            // main cover top supports
            for (px_wy=[[-mb_base_wx_o/2+mb_base_er_wx+cover_tol,mc_ts_wy],[mc_mh_pxl[1]-mc_ts_wx/2,mc_ts_wy+cover_channel_width],[mc_mh_pxl[0]-mc_ts_wx/2,mc_ts_wy+cover_channel_width]]) {
              translate([px_wy[0],mb_base_wy_o+mt_base_d_eff+cover_tol+bevel_w-mc_ts_wy,mb_base_d-ovr])
              cube([mc_ts_wx,px_wy[1]+ovr,main_pcb_wh+2*ovr]);
            }
          }
        }
      union() {
        // main cover p1 (same as above)
        translate([mc_p1_px-bevel_w,0,0])
        cube([sb_base_wx_o+2*bevel_w,mb_base_wy_o+mt_base_d_eff+mc_cc_wy+2*bevel_w,main_pcb_wh+mb_base_d+bevel_w]);
        // main cover p2 (same as above)
        translate([-mb_base_wx_o/2-bevel_w,0,0])
        cube([mb_base_wx_o+2*bevel_w,mb_base_wy_o+mt_base_d_eff+2*bevel_w,main_pcb_wh+mb_base_d+bevel_w]);
      }
      }
      union() {
        for (mc_mh_px=mc_mh_pxl) {
          // mounting hole
          translate([mc_mh_px,mc_mh_py,-ovr])
          cylinder(h=main_pcb_wh+mb_base_d+bevel_w+2*ovr,r=mc_mh_wr_h_ch);
          // mounting hole top
          translate([mc_mh_px,mc_mh_py,mc_mh_pz_st+bevel_w])
          cylinder(h=main_pcb_wh+mb_base_d-mc_mh_pz_st+ovr,r=mc_mh_wr_h_hch);
          translate([mc_mh_px-mc_mh_wr_h_hch,mc_mh_py,mc_mh_pz_st+bevel_w])
          cube([2*mc_mh_wr_h_hch,mc_mh_wr_h_hch+big,main_pcb_wh+mb_base_d-mc_mh_pz_st]);
        }
      }
    }
  }
}

sensor_pcb_wh = 4.0; // components and pcb // measured 3.14 mm but we need room for cables to bend over
sc_cc_wy = cover_channel_width;
sc_irh_px = 2.5; // ir hole
sc_irh_py = 7;
sc_irh_wx = 17.5;
sc_irh_wy = (rows_of_leds_populated == 2 ? 18-sc_irh_py : (rows_of_leds_populated == 1 ? 12-sc_irh_py : 0));
sc_irw_ww = 3.5; // ir window  
sc_irw_px = 2.5-sc_irw_ww;
sc_irw_py = 7-sc_irw_ww;
sc_irw_wz = ir_led_window_plastic_thickness;
sc_irw_wx = sc_irh_wx+2*sc_irw_ww; 
sc_irw_wy = sc_irh_wy+2*sc_irw_ww;
sc_mh_wr_s = 2;
sc_mh_wr_h_st = m1_4_wd_h_st/2;
sc_mh_pxl = [-sensor_pcb_wx*0.45,sensor_pcb_wx*0.45];
sc_mh_py = sb_base_wy_o+st_base_d+sc_cc_wy+bevel_w-cover_screw_vertical_pos;

module cover_sensor() {
  translate([sensor_o_x,sensor_o_y,sensor_o_z])
  rotate([0,180,0])
  union () {
    difference() {
      union() {
        // main cover
        translate([-sb_base_wx_o/2-bevel_w,0,-tv_bezel_thickness])
        cube([sb_base_wx_o+2*bevel_w,sb_base_wy_o+st_base_d+sc_cc_wy+2*bevel_w,sensor_pcb_wh+sc_irw_wz+sb_base_d+tv_bezel_thickness+bevel_w]);
      }
      union() {
        // main cutaway
        translate([-sb_base_wx_o/2-cover_tol,bevel_w-cover_tol,-tv_bezel_thickness-ovr])
        cube([sb_base_wx_o+2*cover_tol,sb_base_wy_o+2*cover_tol+st_base_d+sc_cc_wy,sensor_pcb_wh+sb_base_d+tv_bezel_thickness]);
        // secondary cutaway
        translate([-sb_base_wx_o/2-bevel_w-2*ovr,-ovr,-tv_bezel_thickness-ovr])
        cube([sb_base_wx_o+2*bevel_w+4*ovr,sb_base_wy_o+st_base_d+bevel_w+cover_tol+ovr,tv_bezel_thickness+bevel_d+cover_tol+ovr]);
        // ir window cutaway
        translate([-sensor_pcb_wx/2+sc_irw_px,sb_base_w_oy+bevel_w+sc_irw_py,sensor_pcb_wh+sb_base_d-ovr])
        cube([sc_irw_wx,sc_irw_wy,sc_irw_wz+2*ovr]);
        // ir led cutaway
        translate([-sensor_pcb_wx/2+sc_irh_px,sb_base_w_oy+bevel_w+sc_irh_py,sensor_pcb_wh++sb_base_d-ovr])
        cube([sc_irh_wx,sc_irh_wy,bevel_d+sc_irw_wz+2*ovr]);
      }
    }
    difference() {
      union() {
        for (sc_mh_px=sc_mh_pxl) {
          // mounting hole standoff
          translate([sc_mh_px,sc_mh_py,-tv_bezel_thickness])
          cylinder(h=sensor_pcb_wh+sc_irw_wz+sb_base_d+tv_bezel_thickness,r=sc_mh_wr_s);
          translate([sc_mh_px-sc_mh_wr_s,sc_mh_py,-tv_bezel_thickness])
          cube([2*sc_mh_wr_s,sb_base_wy_o+st_base_d+sc_cc_wy+2*bevel_w-sc_mh_py,sensor_pcb_wh+sc_irw_wz+sb_base_d+tv_bezel_thickness]);
        }
      }
      union() {
        for (sc_mh_px=sc_mh_pxl) {
          // mounting hole
          translate([sc_mh_px,sc_mh_py,-tv_bezel_thickness-ovr])
          cylinder(h=sensor_pcb_wh+sc_irw_wz+sb_base_d+tv_bezel_thickness+ovr,r=sc_mh_wr_h_st);
        }
      }
    }
  }
}


build_split_base = 0; // For users who need a simple mount they can use on different TV's for testing
build_base = 0;
build_cover_main = 0;
build_cover_sensor = 0;

if (orientate_print_ready == "yes") {
  translate([0,0,mb_base_wy_o+bevel_w+mt_base_d_eff])rotate([-90,0,0])base();
  translate([+mb_base_wx_o+2*bevel_w+5,0,main_pcb_wh+mb_base_d+bevel_w])rotate([180,0,0])cover_main();
  translate([-mb_base_wx_o-2*bevel_w-5,-mb_base_wy_o-bevel_w-mt_base_d_eff,sensor_pcb_wh+sb_base_d+tv_bezel_thickness+bevel_w])cover_sensor();
}
else if (build_split_base == 1)
{
  difference() {
    base();
    translate([-mb_base_wx_o/2-bevel_w-ovr,0,-0.49*tv_bezel_thickness])cube([mb_base_wx_o+2*bevel_w+2*ovr,1000,0.02*tv_bezel_thickness]);
  }
}
else if (build_base == 1)
{
  base();
}
else if (build_cover_main == 1)
{
  cover_main();
}
else if (build_cover_sensor == 1)
{
  cover_sensor();
}
else {
  base();
  color(c=[0.5,0,0.5,0.25])translate([0,0,explode])cover_main();
  color(c=[0.5,0.5,0,0.25])translate([0,0,-explode])cover_sensor();
}