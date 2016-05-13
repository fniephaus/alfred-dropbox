all: clean build

build:
	cd src ; \
	zip ../Dropbox-Client-for-Alfred.alfredworkflow . -r --exclude=*.DS_Store* --exclude=*.pyc*

clean:
	rm -f *.alfredworkflow

update-lib:
	pip download -d ./ Alfred-Workflow
	tar xzvf Alfred-Workflow-*.tar.gz
	cp -r Alfred-Workflow-*/workflow src/
	rm -rf Alfred-Workflow-*
