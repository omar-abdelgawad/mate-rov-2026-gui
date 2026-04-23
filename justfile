# lists recipes
default:
  just --list

run_gui:
  cd src/rov_gui && python main.py

test_mobile_rtsp:
  python ./scripts/test_gstreamer_mobile.py

fmt:
  uvx ruff format src

lint-fix:
  uvx ruff check src/ --fix

[doc('dry run of git clean. use clean force to delete')]
clean mode="dry":
    git clean -fxfd -e '*venv' -e '.env' {{ if mode == "force" { "" } else { "--dry-run" } }}

