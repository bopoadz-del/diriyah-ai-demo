PROJECT=diriyah-brain-ai
COMPOSE=docker-compose -f docker-compose.override.yml
NAMESPACE=default
K8S_DIR=deploy/k8s

up: ; $(COMPOSE) up --build -d
down: ; $(COMPOSE) down
restart: ; $(COMPOSE) down && $(COMPOSE) up --build -d
ps: ; $(COMPOSE) ps
logs: ; $(COMPOSE) logs -f

backend-shell: ; $(COMPOSE) exec backend /bin/bash || $(COMPOSE) exec backend /bin/sh
frontend-shell: ; $(COMPOSE) exec frontend /bin/sh
redis-cli: ; $(COMPOSE) exec redis redis-cli
chroma-shell: ; $(COMPOSE) exec chroma /bin/sh

logs-backend: ; $(COMPOSE) logs -f backend
logs-frontend: ; $(COMPOSE) logs -f frontend
logs-redis: ; $(COMPOSE) logs -f redis
logs-chroma: ; $(COMPOSE) logs -f chroma

prune: ; docker system prune -af --volumes
test: ; $(COMPOSE) exec backend pytest -q

k8s-apply: ; kubectl apply -f $(K8S_DIR)/deployment.yaml -n $(NAMESPACE)
k8s-delete: ; kubectl delete -f $(K8S_DIR)/deployment.yaml -n $(NAMESPACE)

k8s-logs-backend: ; kubectl logs -l app=backend -n $(NAMESPACE) -f
k8s-logs-frontend: ; kubectl logs -l app=frontend -n $(NAMESPACE) -f

k8s-port-backend: ; kubectl port-forward svc/backend 8000:8000 -n $(NAMESPACE)
k8s-port-frontend: ; kubectl port-forward svc/frontend 3000:80 -n $(NAMESPACE)

k8s-test: ; kubectl exec -it $$(kubectl get pod -l app=backend -n $(NAMESPACE) -o jsonpath='{.items[0].metadata.name}') -n $(NAMESPACE) -- pytest -q
