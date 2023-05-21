.PHONY: lexer parser clean

all: lexer parser

lexer:
	mkdir -p parser
	antlr4 -o parser -visitor -Dlanguage=Python3 java_grammars/JavaLexer.g4
	mv parser/java_grammars parser/lexer
parser:
	antlr4 -o parser -visitor -Dlanguage=Python3 -lib parser/lexer java_grammars/JavaParser.g4 
	mv parser/java_grammars/* parser
	rmdir parser/java_grammars
clean:
	rm -rf ./parser
