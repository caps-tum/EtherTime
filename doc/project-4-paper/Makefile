MAKE = make

.PHONY: all clean diff view edit single

# Change this to something like 'rtas23' once the target conference is clear.
NAME = draft

MAIN = project-4-paper

# Add any custom .cls, .bst, or .sty files needed to compile.
# Used only by 'make single'.
STYLE_FILES =

ALL = ${MAIN}.pdf

TEX   := $(shell find . -name '*.tex')
MDTEX := $(shell find . -name '*.md' ! -name 'README.md' | sed 's/.md/.from-md.tex/')
BIB   := $(shell find . -name '*.bib')

all: ${ALL} ${MDTEX}

${MAIN}.pdf: ${TEX} ${BIB} ${MDTEX}
	latexmk -pdf ${MAIN}.tex

EXTS  = *~ *.aux *.backup *.blg *.log *.out *.vtc *.lof *.loa *.lot *.toc *.bbl *.bak *.texshop *.dvi *.fdb_latexmk *.fls
TRASH := $(foreach ext,${EXTS},$(shell find . -name '${ext}'))

%.from-md.tex: %.md
	@echo "[Markdown -> LaTeX]" $<
	@(echo "%%% !!!! AUTO-GENERATED: Do not edit!"; pandoc -f markdown -t latex $<) \
	 | sed -e '/\\tightlist/d' -e '/\\\labelenumi/d' > $@

draft: ${MAIN}.pdf
	@mv -v ${MAIN}.pdf ${NAME}-$(shell date "+%Y-%m-%d-%H%M").pdf

clean:
	@echo Cleaning  ${EXTS} ${ALL}...
	@latexmk -C -quiet ${MAIN}.tex
	@rm -f ${EXTS} ${TRASH} ${MDTEX}

view: ${MAIN}.pdf
	@latexmk -pv -view=pdf ${MAIN}.tex

edit: 
	open ${MAIN}.tex

DIST ?= /tmp/${NAME}-for-distribution

# depends on 'all' because we need the .fls file to be generated first.
single: all
	rm -rf "${DIST}"
	mkdir -p "${DIST}"
	latexpand --fatal  --empty-comments ${MAIN}.tex > ${DIST}/${NAME}.tex
	for F in ${BIB} ${STYLE_FILES}; do mkdir -p ${DIST}/$$(dirname $$F); cp -v $$F ${DIST}/$$F; done
	for F in $$(egrep 'INPUT .*\.(pdf|eps|png|jpeg|jpg)' ${MAIN}.fls | sed -e 's/INPUT //' -e 's|\./||' | sort | uniq); do mkdir -p ${DIST}/$$(dirname $$F); cp -v $$F ${DIST}/$$F; done
	(cd ${DIST}; latexmk -pdf ${NAME}.tex && latexmk -pv -view=pdf ${NAME}.tex && latexmk -c ${NAME}.tex)
	@echo
	@echo 
	@echo Single-file distribution ready.
	@echo See: ${DIST}
	@echo

# By default, compare against the last tag.
DEFAULTBASE := $(shell git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo 'HEAD^' )

BASE ?= ${DEFAULTBASE}
HEAD ?= HEAD

BASE_SHORT ?= $(shell git rev-parse --short ${BASE})
HEAD_SHORT ?= $(shell git rev-parse --short ${HEAD})

# requires git-latexdiff --- see https://gitlab.com/git-latexdiff/git-latexdiff
diff:
	@echo "Diffing from ${BASE_SHORT} to ${HEAD_SHORT}..."
	git latexdiff --main ${MAIN}.tex --latexmk  \
		${BASE_SHORT} ${HEAD_SHORT} \
		--verbose \
		-o diff-${HEAD_SHORT}-to-${BASE_SHORT}.pdf \
		--ignore-latex-errors
	@if [ `uname` = "Darwin" ]; then open diff-${HEAD_SHORT}-to-${BASE_SHORT}.pdf; fi
