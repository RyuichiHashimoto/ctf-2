.PHONY: up down restart log \
        up-backend down-backend restart-backend log-backend exec-backend \
        up-frontend down-frontend restart-frontend log-frontend exec-frontend \
        up-db down-db restart-db log-db \
        check upload pipeline


## ------------------  全サービス  ------------------

up:
	docker compose up -d --build

down:
	docker compose down

restart: down up

log:
	docker compose logs -f


## ------------------  backend  ------------------

up-backend:
	docker compose up -d --build backend

down-backend:
	docker compose down backend

restart-backend: down-backend up-backend

log-backend:
	docker compose logs backend -f

exec-backend:
	docker compose exec backend /bin/bash


## ------------------  frontend-angular  ------------------

up-frontend:
	docker compose up -d --build frontend-angular

down-frontend:
	docker compose down frontend-angular

restart-frontend: down-frontend up-frontend

log-frontend:
	docker compose logs frontend-angular -f

exec-frontend:
	docker compose exec frontend-angular /bin/bash


## ------------------  DB (MySQL)  ------------------

up-db:
	docker compose up -d mysql

down-db:
	docker compose down mysql

restart-db: down-db up-db

log-db:
	docker compose logs mysql -f


## ------------------  開発ユーティリティ  ------------------

# Python 構文確認
check:
	python3 -m compileall backend/src

# グラフ JSON アップロード
# 使い方: make upload FILE=path/to/graph.json
upload:
	./scripts/upload-system-config.sh $(FILE)

# パイプライン実験実行（sample_input / sample_config を使用）
# 使い方: make pipeline
#         make pipeline INPUT=src/experiments/my_input.json
#         make pipeline AUGMENTATION=full_mesh TOP_K=10 EXPERIMENT_ID=exp001
# pipeline:
# 	cd backend && PYTHONPATH=src python3 src/experiments/run_attack_pipeline.py \
# 		--input  $(or $(INPUT),src/experiments/sample_input.json) \
# 		--config $(or $(CONFIG),src/experiments/sample_config.json) \
# 		$(if $(AUGMENTATION),--augmentation-mode $(AUGMENTATION)) \
# 		$(if $(TOP_K),--top-k $(TOP_K)) \
# 		$(if $(MAX_NODES),--max-nodes $(MAX_NODES)) \
# 		$(if $(EXPERIMENT_ID),--experiment-id $(EXPERIMENT_ID)) \
# 		$(if $(RESULT_DIR),--result-dir $(RESULT_DIR))
