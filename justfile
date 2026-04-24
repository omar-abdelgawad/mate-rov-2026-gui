# note that you always have to source your environment before running any command 
default_ip := "192.168.0.57" # we set this manually as a static ip on the pi
# lists recipes
default:
  just --list

run_gui:
  cd src/rov_gui && python main.py

test_mobile_rtsp ip="" port="":
  python ./scripts/test_gstreamer_mobile.py {{ip}} {{port}}

test_mobile_rtsp_2 ip="" port="":
  python ./scripts/test_gstreamer_mobile_2.py {{ip}} {{port}}

test_gui_mobile +rtsp_urls="rtsp://192.168.1.15:8080/h264_ulaw.sdp":
  cd src/rov_gui && python main.py --mobile-rtsp {{rtsp_urls}}

test_gui_cameras ip=default_ip:
  just test_gui_mobile "rtsp://{{ip}}:5000/unicast" "rtsp://{{ip}}:5002/unicast" "rtsp://{{ip}}:8554/zed"

test_one_camera port='5000' ip=default_ip :
  ffplay -rtsp_transport tcp rtsp://{{ip}}:{{port}}/unicast
test_zed_camera ip=default_ip port='8554':
  ffplay -rtsp_transport tcp rtsp://{{ip}}:{{port}}/zed
  
fmt:
  uvx ruff format src

lint-fix:
  uvx ruff check src/ --fix

[doc('dry run of git clean. use clean force to delete')]
clean mode="dry":
    git clean -fxfd -e '*venv' -e '.env' {{ if mode == "force" { "" } else { "--dry-run" } }}

[doc('Run the standalone joystick node manually')]
run_joystick:
  python ./scripts/joystick.py
