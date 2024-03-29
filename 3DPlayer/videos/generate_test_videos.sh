#!/usr/bin/env bash

timeout --signal SIGINT 5 \
gst-launch-1.0 -e \
videomixer name=mix background=0 \
        sink_1::xpos=0   sink_1::ypos=0 \
        sink_2::xpos=1920 sink_2::ypos=0 \
    ! x264enc ! mp4mux ! filesink location=ghosting_test_video_1080p_black_left_white_right_side_by_side_full.mp4 \
videotestsrc pattern=black \
    ! videoscale \
    ! video/x-raw,width=1920,height=1080  \
    ! mix.sink_1 \
videotestsrc pattern=white \
    ! videoscale \
    ! video/x-raw,width=1920,height=1080  \
    ! mix.sink_2

timeout --signal SIGINT 5 \
gst-launch-1.0 -e \
videomixer name=mix background=0 \
        sink_1::xpos=0   sink_1::ypos=0 \
        sink_2::xpos=1920 sink_2::ypos=0 \
    ! x264enc ! mp4mux ! filesink location=ghosting_test_video_1080p_red_left_blue_right_side_by_side_full.mp4 \
videotestsrc pattern=red \
    ! videoscale \
    ! video/x-raw,width=1920,height=1080  \
    ! mix.sink_1 \
videotestsrc pattern=blue \
    ! videoscale \
    ! video/x-raw,width=1920,height=1080  \
    ! mix.sink_2

timeout --signal SIGINT 5 \
gst-launch-1.0 -e \
videomixer name=mix background=0 \
        sink_1::xpos=0   sink_1::ypos=0 \
        sink_2::xpos=1920 sink_2::ypos=0 \
    ! x264enc ! mp4mux ! filesink location=scaling_test_video_1080p_red_left_blue_right_side_by_side_full.mp4 \
videotestsrc pattern=red \
    ! videoscale \
    ! video/x-raw,width=1900,height=1060  \
    ! videobox autocrop=true fill=green \
    ! video/x-raw,width=1920,height=1080  \
    ! mix.sink_1 \
videotestsrc pattern=blue \
    ! videoscale \
    ! video/x-raw,width=1900,height=1060  \
    ! videobox autocrop=true fill=yellow \
    ! video/x-raw,width=1920,height=1080  \
    ! mix.sink_2
    
timeout --signal SIGINT 5 \
gst-launch-1.0 -e \
videomixer name=mix background=0 \
        sink_1::xpos=0   sink_1::ypos=0 \
        sink_2::xpos=0   sink_2::ypos=1080 \
    ! x264enc ! mp4mux ! filesink location=scaling_test_video_1080p_red_top_blue_bottom_over_and_under_full.mp4 \
videotestsrc pattern=red \
    ! videoscale \
    ! video/x-raw,width=1900,height=1060  \
    ! videobox autocrop=true fill=green \
    ! video/x-raw,width=1920,height=1080  \
    ! mix.sink_1 \
videotestsrc pattern=blue \
    ! videoscale \
    ! video/x-raw,width=1900,height=1060  \
    ! videobox autocrop=true fill=yellow \
    ! video/x-raw,width=1920,height=1080  \
    ! mix.sink_2
    
timeout --signal SIGINT 5 \
gst-launch-1.0 -e \
videomixer name=mix background=0 \
        sink_1::xpos=0   sink_1::ypos=0 \
        sink_2::xpos=960 sink_2::ypos=0 \
    ! x264enc ! mp4mux ! filesink location=scaling_test_video_1080p_red_left_blue_right_side_by_side_half.mp4 \
videotestsrc pattern=red \
    ! videoscale \
    ! video/x-raw,width=950,height=1060  \
    ! videobox autocrop=true fill=green \
    ! video/x-raw,width=960,height=1080  \
    ! mix.sink_1 \
videotestsrc pattern=blue \
    ! videoscale \
    ! video/x-raw,width=950,height=1060  \
    ! videobox autocrop=true fill=yellow \
    ! video/x-raw,width=960,height=1080  \
    ! mix.sink_2
    
timeout --signal SIGINT 5 \
gst-launch-1.0 -e \
videomixer name=mix background=0 \
        sink_1::xpos=0   sink_1::ypos=0 \
        sink_2::xpos=0   sink_2::ypos=540 \
    ! x264enc ! mp4mux ! filesink location=scaling_test_video_1080p_red_top_blue_bottom_over_and_under_half.mp4 \
videotestsrc pattern=red \
    ! videoscale \
    ! video/x-raw,width=1900,height=530  \
    ! videobox autocrop=true fill=green \
    ! video/x-raw,width=1920,height=540  \
    ! mix.sink_1 \
videotestsrc pattern=blue \
    ! videoscale \
    ! video/x-raw,width=1900,height=530  \
    ! videobox autocrop=true fill=yellow \
    ! video/x-raw,width=1920,height=540  \
    ! mix.sink_2

timeout --signal SIGINT 5 \
gst-launch-1.0 -e \
videomixer name=mix background=0 \
        sink_1::xpos=0   sink_1::ypos=0 \
        sink_2::xpos=1280 sink_2::ypos=0 \
    ! x264enc ! mp4mux ! filesink location=scaling_test_video_720p_red_left_blue_right_side_by_side_full.mp4 \
videotestsrc pattern=red \
    ! videoscale \
    ! video/x-raw,width=1260,height=700  \
    ! videobox autocrop=true fill=green \
    ! video/x-raw,width=1280,height=720  \
    ! mix.sink_1 \
videotestsrc pattern=blue \
    ! videoscale \
    ! video/x-raw,width=1260,height=700  \
    ! videobox autocrop=true fill=yellow \
    ! video/x-raw,width=1280,height=720  \
    ! mix.sink_2
    
timeout --signal SIGINT 5 \
gst-launch-1.0 -e \
videomixer name=mix background=0 \
        sink_1::xpos=0   sink_1::ypos=0 \
        sink_2::xpos=0   sink_2::ypos=720 \
    ! x264enc ! mp4mux ! filesink location=scaling_test_video_720p_red_top_blue_bottom_over_and_under_full.mp4 \
videotestsrc pattern=red \
    ! videoscale \
    ! video/x-raw,width=1260,height=700  \
    ! videobox autocrop=true fill=green \
    ! video/x-raw,width=1280,height=720  \
    ! mix.sink_1 \
videotestsrc pattern=blue \
    ! videoscale \
    ! video/x-raw,width=1260,height=700  \
    ! videobox autocrop=true fill=yellow \
    ! video/x-raw,width=1280,height=720  \
    ! mix.sink_2
    
timeout --signal SIGINT 5 \
gst-launch-1.0 -e \
videomixer name=mix background=0 \
        sink_1::xpos=0   sink_1::ypos=0 \
        sink_2::xpos=640 sink_2::ypos=0 \
    ! x264enc ! mp4mux ! filesink location=scaling_test_video_720p_red_left_blue_right_side_by_side_half.mp4 \
videotestsrc pattern=red \
    ! videoscale \
    ! video/x-raw,width=630,height=700  \
    ! videobox autocrop=true fill=green \
    ! video/x-raw,width=640,height=720  \
    ! mix.sink_1 \
videotestsrc pattern=blue \
    ! videoscale \
    ! video/x-raw,width=630,height=700  \
    ! videobox autocrop=true fill=yellow \
    ! video/x-raw,width=640,height=720  \
    ! mix.sink_2
    
timeout --signal SIGINT 5 \
gst-launch-1.0 -e \
videomixer name=mix background=0 \
        sink_1::xpos=0   sink_1::ypos=0 \
        sink_2::xpos=0   sink_2::ypos=360 \
    ! x264enc ! mp4mux ! filesink location=scaling_test_video_720p_red_top_blue_bottom_over_and_under_half.mp4 \
videotestsrc pattern=red \
    ! videoscale \
    ! video/x-raw,width=1260,height=350  \
    ! videobox autocrop=true fill=green \
    ! video/x-raw,width=1280,height=360  \
    ! mix.sink_1 \
videotestsrc pattern=blue \
    ! videoscale \
    ! video/x-raw,width=1260,height=350  \
    ! videobox autocrop=true fill=yellow \
    ! video/x-raw,width=1280,height=360  \
    ! mix.sink_2

timeout --signal SIGINT 5 \
gst-launch-1.0 -e \
videomixer name=mix background=0 \
        sink_1::xpos=0   sink_1::ypos=0 \
        sink_2::xpos=960 sink_2::ypos=0 \
    ! x264enc ! mp4mux ! filesink location=scaling_test_video_540p_red_left_blue_right_side_by_side_full.mp4 \
videotestsrc pattern=red \
    ! videoscale \
    ! video/x-raw,width=940,height=520  \
    ! videobox autocrop=true fill=green \
    ! video/x-raw,width=960,height=540  \
    ! mix.sink_1 \
videotestsrc pattern=blue \
    ! videoscale \
    ! video/x-raw,width=940,height=520  \
    ! videobox autocrop=true fill=yellow \
    ! video/x-raw,width=960,height=540  \
    ! mix.sink_2
    
timeout --signal SIGINT 5 \
gst-launch-1.0 -e \
videomixer name=mix background=0 \
        sink_1::xpos=0   sink_1::ypos=0 \
        sink_2::xpos=0   sink_2::ypos=540 \
    ! x264enc ! mp4mux ! filesink location=scaling_test_video_540p_red_top_blue_bottom_over_and_under_full.mp4 \
videotestsrc pattern=red \
    ! videoscale \
    ! video/x-raw,width=940,height=520  \
    ! videobox autocrop=true fill=green \
    ! video/x-raw,width=960,height=540  \
    ! mix.sink_1 \
videotestsrc pattern=blue \
    ! videoscale \
    ! video/x-raw,width=940,height=520  \
    ! videobox autocrop=true fill=yellow \
    ! video/x-raw,width=960,height=540  \
    ! mix.sink_2
    
timeout --signal SIGINT 5 \
gst-launch-1.0 -e \
videomixer name=mix background=0 \
        sink_1::xpos=0   sink_1::ypos=0 \
        sink_2::xpos=480 sink_2::ypos=0 \
    ! x264enc ! mp4mux ! filesink location=scaling_test_video_540p_red_left_blue_right_side_by_side_half.mp4 \
videotestsrc pattern=red \
    ! videoscale \
    ! video/x-raw,width=470,height=520  \
    ! videobox autocrop=true fill=green \
    ! video/x-raw,width=480,height=540  \
    ! mix.sink_1 \
videotestsrc pattern=blue \
    ! videoscale \
    ! video/x-raw,width=470,height=520  \
    ! videobox autocrop=true fill=yellow \
    ! video/x-raw,width=480,height=540  \
    ! mix.sink_2
    
timeout --signal SIGINT 5 \
gst-launch-1.0 -e \
videomixer name=mix background=0 \
        sink_1::xpos=0   sink_1::ypos=0 \
        sink_2::xpos=0   sink_2::ypos=270 \
    ! x264enc ! mp4mux ! filesink location=scaling_test_video_540p_red_top_blue_bottom_over_and_under_half.mp4 \
videotestsrc pattern=red \
    ! videoscale \
    ! video/x-raw,width=940,height=260  \
    ! videobox autocrop=true fill=green \
    ! video/x-raw,width=960,height=270  \
    ! mix.sink_1 \
videotestsrc pattern=blue \
    ! videoscale \
    ! video/x-raw,width=940,height=260  \
    ! videobox autocrop=true fill=yellow \
    ! video/x-raw,width=960,height=270  \
    ! mix.sink_2
