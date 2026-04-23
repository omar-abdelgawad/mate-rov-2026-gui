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

test_gui_cameras:
  just test_gui_mobile "rtsp://192.168.0.100:5000/unicast" "rtsp://192.168.0.100:5001/unicast" "rtsp://192.168.0.100:5002/unicast" "rtsp://192.168.0.100:5003/unicast" "rtsp://192.168.0.100:5004/unicast"

test_one_camera port='5000':
  ffplay -rtsp_transport tcp rtsp://192.168.0.100:{{port}}/unicast
fmt:
  uvx ruff format src

lint-fix:
  uvx ruff check src/ --fix

[doc('dry run of git clean. use clean force to delete')]
clean mode="dry":
    git clean -fxfd -e '*venv' -e '.env' {{ if mode == "force" { "" } else { "--dry-run" } }}

