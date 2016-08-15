CONTAINER_DIR := /code

all: test

pip:
	pip install -r requirements.txt

test: pip
	nosetests

docker:
	# create a container
	$(eval CONTAINER_ID := $(shell docker create \
		-i \
		-w $(CONTAINER_DIR) \
		python:2.7 \
		make test\
	))
	
	# run build inside container
	docker cp . $(CONTAINER_ID):$(CONTAINER_DIR)/
	
	# start command
	docker start -a -i $(CONTAINER_ID)

	# remove container
	docker rm $(CONTAINER_ID)
