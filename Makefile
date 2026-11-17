.PHONY: help install build-frontend pg-init pg-start pg-stop pg-status migrate seed train train-code train-video train-human-video train-trump-video generate-trump-video train-audio train-images train-reset start stop restart reload pkill status logs test clean-images clean-video clean-media clean

SHELL := /bin/bash
ROOT_DIR := $(CURDIR)
SRC_ROOT := $(ROOT_DIR)/src
BASE_DIR := $(SRC_ROOT)/base
RUN_DIR := $(BASE_DIR)/.run
LOG_DIR := $(BASE_DIR)/.logs
PGDATA_DIR := $(BASE_DIR)/.pgdata
BACKEND_DIR := $(SRC_ROOT)/backend
FRONTEND_DIR := $(SRC_ROOT)/frontend
POSTGRAPHQL_DIR := $(BASE_DIR)/postgraphql

POETRY_BIN := $(shell command -v poetry 2>/dev/null || (test -x "$(HOME)/.local/bin/poetry" && echo "$(HOME)/.local/bin/poetry"))
VENV_BIN_DIR := $(dir $(firstword $(wildcard $(HOME)/.cache/pypoetry/virtualenvs/ai-model-*/bin/python)))
PYTHON_RUN := $(if $(POETRY_BIN),$(POETRY_BIN) run python,$(if $(VENV_BIN_DIR),$(VENV_BIN_DIR)python,python3))
PYTEST_RUN := $(if $(POETRY_BIN),$(POETRY_BIN) run pytest,$(if $(VENV_BIN_DIR),$(VENV_BIN_DIR)pytest,pytest))
UVICORN_RUN := $(if $(POETRY_BIN),$(POETRY_BIN) run uvicorn,$(if $(VENV_BIN_DIR),$(VENV_BIN_DIR)uvicorn,uvicorn))
NPM ?= $(shell command -v npm 2>/dev/null || echo "npm")
NODE ?= $(shell command -v node 2>/dev/null || echo "node")

PG_BIN_DIR ?= $(firstword $(wildcard /usr/lib/postgresql/*/bin) /usr/bin)
POSTGRES_HOST ?= 127.0.0.1
POSTGRES_PORT ?= 5433
POSTGRES_DB ?= ai_model
POSTGRES_USER ?= ai_model
POSTGRES_PASSWORD ?= ai_model_dev_pass

DJANGO_HOST ?= 127.0.0.1
DJANGO_PORT ?= 8000
FASTAPI_HOST ?= 127.0.0.1
FASTAPI_PORT ?= 8001
POSTGRAPHILE_HOST ?= 127.0.0.1
POSTGRAPHILE_PORT ?= 5000
FRONTEND_PORT ?= 5173

help:
	@echo "AI-Model Platform Makefile Targets:"
	@echo "  make install         - Install Python (Poetry), Frontend (npm), and PostGraphile (npm) dependencies"
	@echo "  make pg-init         - Initialize local PostgreSQL cluster in src/base/.pgdata"
	@echo "  make pg-start        - Start local PostgreSQL ($(POSTGRES_HOST):$(POSTGRES_PORT)) and ensure DB exists"
	@echo "  make pg-stop         - Stop local PostgreSQL cluster"
	@echo "  make pg-status       - Check PostgreSQL readiness"
	@echo "  make migrate         - Ensure PostgreSQL is up and run Django makemigrations & migrate"
	@echo "  make seed            - Seed billing plans, starter agents, and demo account"
	@echo "  make train           - Train all ai_engine tiers (--all-tiers) across active backends"
	@echo "  make train-code      - Train all tiers with runnable Code corpus evaluation checks"
	@echo "  make train-video     - Train all tiers with Video motion corpus evaluation checks"
	@echo "  make train-audio     - Train all tiers with Audio speech and acoustic evaluation checks"
	@echo "  make train-images    - Train all tiers with Image generation evaluation checks"
	@echo "  make train-reset     - Reset checkpoints and retrain all ai_engine tiers"
	@echo "  make start           - Start PostgreSQL, Django (:$(DJANGO_PORT)), FastAPI (:$(FASTAPI_PORT)), PostGraphQL (:$(POSTGRAPHILE_PORT)), and React Vite (:$(FRONTEND_PORT))"
	@echo "  make stop            - Gracefully stop services tracked in src/base/.run/*.pid and local PostgreSQL"
	@echo "  make restart         - Stop and start all services"
	@echo "  make reload          - Reload / refresh all active services cleanly"
	@echo "  make pkill           - Force kill all matching ai-model processes and clear PIDs"
	@echo "  make status          - Check status of managed services"
	@echo "  make logs            - Tail recent logs for all services"
	@echo "  make test            - Run pytest test suite"

install:
	@if [ -n "$(POETRY_BIN)" ]; then $(POETRY_BIN) install; else echo "Poetry binary not found on PATH; using existing virtualenv $(VENV_BIN_DIR)"; fi
	cd "$(FRONTEND_DIR)" && $(NPM) install
	cd "$(POSTGRAPHQL_DIR)" && $(NPM) install

build-frontend:
	cd "$(FRONTEND_DIR)" && $(NPM) run build

pg-init:
	@mkdir -p "$(RUN_DIR)" "$(LOG_DIR)"
	@if [ ! -f "$(PGDATA_DIR)/PG_VERSION" ]; then \
		pwfile="$(RUN_DIR)/.pgpass.init"; \
		printf "%s\n" "$(POSTGRES_PASSWORD)" > "$$pwfile"; \
		chmod 600 "$$pwfile"; \
		"$(PG_BIN_DIR)/initdb" -D "$(PGDATA_DIR)" -U "$(POSTGRES_USER)" --encoding=UTF8 --auth=scram-sha-256 --pwfile="$$pwfile" > "$(LOG_DIR)/postgres-init.log" 2>&1; \
		rm -f "$$pwfile"; \
		echo "Initialized local PostgreSQL cluster in $(PGDATA_DIR)"; \
	fi

pg-start: pg-init
	@mkdir -p "$(RUN_DIR)" "$(LOG_DIR)"
	@if "$(PG_BIN_DIR)/pg_isready" -h "$(POSTGRES_HOST)" -p "$(POSTGRES_PORT)" >/dev/null 2>&1 || \
	    "$(PG_BIN_DIR)/pg_isready" -h "$(RUN_DIR)" -p "$(POSTGRES_PORT)" >/dev/null 2>&1; then \
		echo "PostgreSQL already accepting connections on $(POSTGRES_HOST):$(POSTGRES_PORT)"; \
	elif "$(PG_BIN_DIR)/pg_ctl" -D "$(PGDATA_DIR)" status >/dev/null 2>&1; then \
		echo "Local PostgreSQL cluster already running on $(POSTGRES_HOST):$(POSTGRES_PORT)"; \
	else \
		rm -f "$(PGDATA_DIR)/postmaster.pid" "$(RUN_DIR)"/.s.PGSQL.*; \
		for shmid in $$(ipcs -m 2>/dev/null | awk -v u="$$USER" '$$3 == u {print $$2}'); do \
			ipcrm -m "$$shmid" 2>/dev/null || true; \
		done; \
		"$(PG_BIN_DIR)/pg_ctl" -D "$(PGDATA_DIR)" -l "$(LOG_DIR)/postgres.log" -o "-k $(RUN_DIR) -h $(POSTGRES_HOST) -p $(POSTGRES_PORT)" start; \
		echo "Started local PostgreSQL on $(POSTGRES_HOST):$(POSTGRES_PORT)"; \
	fi
	@PGPASSWORD="$(POSTGRES_PASSWORD)" "$(PG_BIN_DIR)/psql" -h "$(POSTGRES_HOST)" -p "$(POSTGRES_PORT)" -U "$(POSTGRES_USER)" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$(POSTGRES_DB)'" 2>/dev/null | grep -q 1 || \
	 PGPASSWORD="$(POSTGRES_PASSWORD)" "$(PG_BIN_DIR)/psql" -h "$(RUN_DIR)" -p "$(POSTGRES_PORT)" -U "$(POSTGRES_USER)" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$(POSTGRES_DB)'" 2>/dev/null | grep -q 1 || \
	 (PGPASSWORD="$(POSTGRES_PASSWORD)" "$(PG_BIN_DIR)/createdb" -h "$(POSTGRES_HOST)" -p "$(POSTGRES_PORT)" -U "$(POSTGRES_USER)" "$(POSTGRES_DB)" 2>/dev/null || \
	  PGPASSWORD="$(POSTGRES_PASSWORD)" "$(PG_BIN_DIR)/createdb" -h "$(RUN_DIR)" -p "$(POSTGRES_PORT)" -U "$(POSTGRES_USER)" "$(POSTGRES_DB)" 2>/dev/null || true)

pg-stop:
	@if "$(PG_BIN_DIR)/pg_isready" -h "$(POSTGRES_HOST)" -p "$(POSTGRES_PORT)" >/dev/null 2>&1 || \
	    "$(PG_BIN_DIR)/pg_isready" -h "$(RUN_DIR)" -p "$(POSTGRES_PORT)" >/dev/null 2>&1; then \
		"$(PG_BIN_DIR)/pg_ctl" -D "$(PGDATA_DIR)" stop -m fast || true; \
	fi
	@rm -f "$(PGDATA_DIR)/postmaster.pid" "$(RUN_DIR)"/.s.PGSQL.*
	@for shmid in $$(ipcs -m 2>/dev/null | awk -v u="$$USER" '$$3 == u {print $$2}'); do \
		ipcrm -m "$$shmid" 2>/dev/null || true; \
	done

pg-status:
	@"$(PG_BIN_DIR)/pg_isready" -h "$(POSTGRES_HOST)" -p "$(POSTGRES_PORT)" 2>/dev/null || \
	 "$(PG_BIN_DIR)/pg_isready" -h "$(RUN_DIR)" -p "$(POSTGRES_PORT)"

migrate: pg-start
	cd "$(BACKEND_DIR)" && $(PYTHON_RUN) manage.py makemigrations billing transactions quota Agent api --noinput
	cd "$(BACKEND_DIR)" && $(PYTHON_RUN) manage.py migrate --noinput

TRAIN_ARGS ?= --all-tiers

seed:
	cd "$(BACKEND_DIR)" && $(PYTHON_RUN) manage.py seed_ai_platform

train: pg-start
	cd "$(BACKEND_DIR)" && $(PYTHON_RUN) manage.py train_ai_engine $(TRAIN_ARGS)

train-code: pg-start
	cd "$(BACKEND_DIR)" && $(PYTHON_RUN) manage.py train_ai_engine $(TRAIN_ARGS) --task code

train-video: pg-start
	cd "$(BACKEND_DIR)" && $(PYTHON_RUN) manage.py train_ai_engine $(TRAIN_ARGS) --task video

train-audio: pg-start
	cd "$(BACKEND_DIR)" && $(PYTHON_RUN) manage.py train_ai_engine $(TRAIN_ARGS) --task audio

train-images: pg-start
	cd "$(BACKEND_DIR)" && $(PYTHON_RUN) manage.py train_ai_engine $(TRAIN_ARGS) --task images

train-chat: pg-start
	cd "$(BACKEND_DIR)" && $(PYTHON_RUN) manage.py train_ai_engine $(TRAIN_ARGS) --task chat $(if $(TXT),--txt $(TXT),)

train-text: train-chat

train-txt: train-chat

generate-audio:
	$(PYTHON_RUN) "$(SRC_ROOT)/ai_engine/training/audio/generate_audio_corpus.py" \
		$(if $(SAMPLES),--samples $(SAMPLES),--samples 1000) \
		$(if $(SIZE_MB),--size-mb $(SIZE_MB),) \
		$(if $(OUT),--output $(OUT),--output "$(SRC_ROOT)/ai_engine/training/audio/audio_corpus_sample.txt")

generate-corpus:
	$(PYTHON_RUN) "$(SRC_ROOT)/ai_engine/training/chat/generate_1b_corpus.py" \
		$(if $(TOKENS),--tokens $(TOKENS),) \
		$(if $(SIZE_MB),--size-mb $(SIZE_MB),) \
		$(if $(SIZE_GB),--size-gb $(SIZE_GB),) \
		$(if $(SAMPLES),--samples $(SAMPLES),) \
		$(if $(OUT),--output $(OUT),--output "$(SRC_ROOT)/ai_engine/training/chat/billion_corpus.txt")

generate-1b:
	$(PYTHON_RUN) "$(SRC_ROOT)/ai_engine/training/chat/generate_1b_corpus.py" --tokens 1B --output "$(SRC_ROOT)/ai_engine/training/chat/billion_corpus.txt"

generate-video-50m:
	$(PYTHON_RUN) "$(SRC_ROOT)/ai_engine/training/video/generate_50m_video_corpus.py" --tokens 50M --output "$(SRC_ROOT)/ai_engine/training/video/video_motion_50m.txt"

train-1b: pg-start
	@if [ ! -f "$(SRC_ROOT)/ai_engine/training/chat/billion_corpus.txt" ]; then \
		echo "Generating 1-Billion token corpus..."; \
		$(MAKE) generate-1b; \
	fi
	cd "$(BACKEND_DIR)" && $(PYTHON_RUN) manage.py train_ai_engine $(TRAIN_ARGS) --task chat --txt "$(SRC_ROOT)/ai_engine/training/chat/billion_corpus.txt" $(if $(MAX_SAMPLES),--max-txt-samples $(MAX_SAMPLES),--max-txt-samples 50000)

train-video-50m: pg-start
	@if [ ! -f "$(SRC_ROOT)/ai_engine/training/video/video_motion_50m.txt" ]; then \
		echo "Generating 50-Million video corpus..."; \
		$(MAKE) generate-video-50m; \
	fi
	cd "$(BACKEND_DIR)" && $(PYTHON_RUN) manage.py train_ai_engine $(TRAIN_ARGS) --task video --txt "$(SRC_ROOT)/ai_engine/training/video/video_motion_50m.txt" $(if $(MAX_SAMPLES),--max-txt-samples $(MAX_SAMPLES),--max-txt-samples 50000)

generate-human-video:
	$(PYTHON_RUN) "$(SRC_ROOT)/ai_engine/training/video/generate_human_video_corpus.py" --size-mb 1.0 --output "$(SRC_ROOT)/ai_engine/training/video/real_virtual_human_video_1m.txt"

train-human-video: pg-start
	@if [ ! -f "$(SRC_ROOT)/ai_engine/training/video/real_virtual_human_video_1m.txt" ]; then \
		echo "Generating 1MB Real & Virtual Human video corpus..."; \
		$(MAKE) generate-human-video; \
	fi
	cd "$(BACKEND_DIR)" && $(PYTHON_RUN) manage.py train_ai_engine $(TRAIN_ARGS) --task video --txt "$(SRC_ROOT)/ai_engine/training/video/real_virtual_human_video_1m.txt" $(if $(MAX_SAMPLES),--max-txt-samples $(MAX_SAMPLES),--max-txt-samples 50000)

generate-trump-video:
	$(PYTHON_RUN) "$(SRC_ROOT)/ai_engine/training/video/generate_trump_funny_video_corpus.py" --size-mb 1.0 --output "$(SRC_ROOT)/ai_engine/training/video/trump_funny_video_1m.txt"

train-trump-video: pg-start
	@if [ ! -f "$(SRC_ROOT)/ai_engine/training/video/trump_funny_video_1m.txt" ]; then \
		echo "Generating 1MB Funny Donald Trump video corpus..."; \
		$(MAKE) generate-trump-video; \
	fi
	cd "$(BACKEND_DIR)" && $(PYTHON_RUN) manage.py train_ai_engine $(TRAIN_ARGS) --task video --txt "$(SRC_ROOT)/ai_engine/training/video/trump_funny_video_1m.txt" $(if $(MAX_SAMPLES),--max-txt-samples $(MAX_SAMPLES),--max-txt-samples 50000)

train-reset: pg-start
	cd "$(BACKEND_DIR)" && $(PYTHON_RUN) manage.py train_ai_engine $(TRAIN_ARGS) --reset

start:
	@$(PYTHON_RUN) "$(BASE_DIR)/dev_supervisor.py"

supervisor:
	@$(PYTHON_RUN) "$(BASE_DIR)/dev_supervisor.py"

stop:
	@if [ -f "$(RUN_DIR)/supervisor.pid" ]; then \
		sup_pid=$$(cat "$(RUN_DIR)/supervisor.pid"); \
		echo "Stopping supervisor (PID $$sup_pid)..."; \
		kill -TERM "$$sup_pid" 2>/dev/null || true; \
		sleep 2; \
	fi
	@for svc in frontend postgraphql fastapi django postgres; do \
		pidfile="$(RUN_DIR)/$$svc.pid"; \
		if [ -f "$$pidfile" ]; then \
			pid=$$(cat "$$pidfile"); \
			if kill -0 "$$pid" 2>/dev/null; then \
				echo "Stopping $$svc (PID $$pid)..."; \
				kill "$$pid" 2>/dev/null || true; \
				sleep 0.5; \
				kill -9 "$$pid" 2>/dev/null || true; \
			fi; \
			rm -f "$$pidfile"; \
		fi; \
	done
	@-pkill -f "node .*server\.cjs" 2>/dev/null || true
	@$(MAKE) pg-stop

restart: stop start

reload:
	@echo "Reloading AI-Model services..."
	@$(MAKE) stop
	@$(MAKE) start

pkill:
	@echo "Force killing AI-Model processes..."
	@-pkill -f "dev_supervisor.py" 2>/dev/null || true
	@-pkill -f "manage.py runserver $(DJANGO_HOST):$(DJANGO_PORT)" 2>/dev/null || true
	@-pkill -f "uvicorn api.main:app" 2>/dev/null || true
	@-pkill -f "node .*server\.cjs" 2>/dev/null || true
	@-pkill -f "$(FRONTEND_DIR)/node_modules/.bin/vite" 2>/dev/null || true
	@$(MAKE) pg-stop || true
	@-rm -f "$(RUN_DIR)"/*.pid "$(RUN_DIR)"/.s.PGSQL.* "$(RUN_DIR)"/status.json
	@for shmid in $$(ipcs -m 2>/dev/null | awk -v u="$$USER" '$$3 == u && $$6 == 0 {print $$2}'); do \
		ipcrm -m "$$shmid" 2>/dev/null || true; \
	done
	@echo "All matching processes terminated."

status:
	@if [ -f "$(RUN_DIR)/status.json" ]; then \
		$(PYTHON_RUN) -c 'import json; d=json.load(open("$(RUN_DIR)/status.json")); print("=== AI-Model Platform Status (" + str(d.get("updated_at", "")) + ") ==="); [print("  %-13s: %-8s (healthy: %-5s, pid: %s)" % (k, str(v.get("status")), str(v.get("healthy")), str(v.get("pid")))) for k, v in d.get("services", {}).items()]'; \
	elif "$(PG_BIN_DIR)/pg_isready" -h "$(POSTGRES_HOST)" -p "$(POSTGRES_PORT)" >/dev/null 2>&1 || \
	    "$(PG_BIN_DIR)/pg_isready" -h "$(RUN_DIR)" -p "$(POSTGRES_PORT)" >/dev/null 2>&1; then \
		echo "postgres: RUNNING ($(POSTGRES_HOST):$(POSTGRES_PORT))"; \
		for svc in django fastapi postgraphql frontend; do \
			pidfile="$(RUN_DIR)/$$svc.pid"; \
			if [ -f "$$pidfile" ] && kill -0 $$(cat "$$pidfile") 2>/dev/null; then \
				echo "$$svc: RUNNING (PID $$(cat "$$pidfile"))"; \
			else \
				echo "$$svc: STOPPED"; \
			fi; \
		done; \
	else \
		echo "All services STOPPED (no status.json or active postgres cluster)."; \
	fi

logs:
	@mkdir -p "$(LOG_DIR)"
	@tail -n 30 "$(LOG_DIR)"/*.log 2>/dev/null || echo "No logs found yet."

test:
	PYTHONPATH="$(BACKEND_DIR):$(SRC_ROOT)" $(PYTEST_RUN) -v tests

check-video:
	@echo "Checking generated video files in $(SRC_ROOT)/ai_engine/media/video/:"
	@find "$(SRC_ROOT)/ai_engine/media/video" -maxdepth 1 -type f -name "*.mp4" -exec ls -lh {} + 2>/dev/null || echo "No video files found."

clean-video:
	@echo "Removing generated MP4 video files..."
	@rm -fv "$(SRC_ROOT)/ai_engine/media/video"/*.mp4 2>/dev/null || true
	@echo "Video directory cleaned."

clean-images:
	@echo "Removing generated image files..."
	@rm -fv "$(SRC_ROOT)/ai_engine/media/images"/* "$(SRC_ROOT)/ai_engine/media/debug_frames"/* 2>/dev/null || true
	@echo "Images directory cleaned."

clean-media: clean-video clean-images
	@echo "Media directory cleaned."

clean: clean-media
	@echo "Cleaning Python bytecode, test caches, and temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.py[cod]" -delete 2>/dev/null || true
	@find . -type f -name "*\$$py.class" -delete 2>/dev/null || true
	@rm -rf .pytest_cache "$(FRONTEND_DIR)/dist" "$(FRONTEND_DIR)/tsconfig.app.tsbuildinfo" /tmp/frame_*.png /tmp/test_*.png
	@echo "Workspace cleaned successfully."
