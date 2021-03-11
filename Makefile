TAG_NAME ?= staging
GHCR_NAME ?= ghcr.io/robopickles/teambot:$(TAG_NAME)

build_ghcr_image:
	docker build -f Dockerfile . -t $(GHCR_NAME)

push_ghcr_image: build_ghcr_image
	@echo Push: $(GHCR_NAME)
	docker push $(GHCR_NAME)

