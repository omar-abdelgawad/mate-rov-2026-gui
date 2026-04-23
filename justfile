# lists recipes
default:
  just --list

run_gui:
  cd src/rov_gui && python main.py

[doc('dry run of git clean. use clean force to delete')]
clean mode="dry":
    git clean -fxfd -e '*venv' -e '.env' {{ if mode == "force" { "" } else { "--dry-run" } }}

