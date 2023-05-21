#!/usr/bin/python3
import sys
import os

import json

from antlr4 import *

from parser.lexer import JavaLexer
from parser import JavaParser
from parser import JavaParserListener
from filter import *

from neo4j import GraphDatabase

class AntlrJavaParser:
    def __init__(self):
        self.filedata = {} # key=filename, value={name, tokens}
        self.results = {}
        self.walker = ParseTreeWalker()

    def read_file(self, filename):
        content = None
        with open(fn, "r", encoding="utf-8") as f:
            content = f.read()
        f.close()
        l = JavaLexer.JavaLexer(InputStream(content))
        tokens = CommonTokenStream(l)
        classname = os.path.basename(fn).split(".")[0]
        self.filedata[filename] = {'name':classname, 'tokens':tokens}
        return True

    def parse_all(self):
        self.results = {}
        for fn in self.filedata.keys():
            classname = self.filedata[fn]["name"]
            tokens = self.filedata[fn]["tokens"]
            #p = JavaParser.JavaParser(tokens)
            p = JavaParser(tokens)
            listener = FilteredListener(classname)
            tree = p.compilationUnit()
            self.walker.walk(listener, tree)
            res = listener.get_results()
            self.results |= res

    def get_results(self, do_parse=True):
        if do_parse:
            self.parse_all()
        return self.results

class Neo4jDB:
    def __init__(self, uri="neo4j://localhost", user="neo4j", password="password"):
        self.uri = uri
        self.user = user
        self.password = password
        self.neo4jdrv = GraphDatabase.driver(uri, auth=(user, password))
        self.session = None
        self.logfile = None

    def __del__(self):
        if self.logfile is not None:
            self.logfile.close()

    def open(self):
        self.logfile = open("db.log", "w")
        if self.session:
            return False
        self.session = self.neo4jdrv.session()

    def create_class_node_if_new(self, name, labels={}):
        query = "MATCH (c:Class{name:'%s'}) return COUNT(c)" % name
        with self.session.begin_transaction() as tx:
            r = tx.run(query).value()[0]
        if (r == 0):
            return self.create_class_node(name, labels)
        return None

    def create_class_node(self, name, labels={}):
        tpl = "CREATE (c:Class{%s})"
        content = []
        labels["name"] = name
        for key in labels:
            content += [key + ':"' + labels[key] + '"']
        query = tpl % ",".join(content)
        self.logfile.write(query + "\n")
        with self.session.begin_transaction() as tx:
            result = tx.run(query)
        return result

    def create_method_node(self, name, labels={}):
        tpl = "CREATE (m:Method{%s})"
        content = []
        labels["name"] = name
        for key in labels:
            content += [key + ':"' + labels[key] + '"']
        query = tpl % ",".join(content)
        self.logfile.write(query + "\n")
        with self.session.begin_transaction() as tx:
            result = tx.run(query)
        return result

    def create_method_node_if_new(self, name, labels={}):
        query = "MATCH (c:Method{name:'%s'}) return COUNT(c)" % name
        with self.session.begin_transaction() as tx:
            r = tx.run(query).value()[0]
        if (r == 0):
            return self.create_method_node(name, labels)
        return None

    def create_class2class_rel(self, rel, c1, c2):
        query = 'MATCH (c1:Class{name:"' + c1 + '"}),' \
                '(c2:Class{name:"' + c2 + '"}) ' \
                'CREATE (c1)-[:' + rel + ']->(c2)'
        self.logfile.write(query + "\n")
        with self.session.begin_transaction() as tx:
            result = tx.run(query)
        return result

    def create_class2method_rel(self, rel, c, m):
        query = 'MATCH (c:Class{name:"' + c + '"}),' \
                '(m:Method{name:"' + m + '"}) ' \
                'CREATE (c)-[:' + rel + ']->(m)'
        self.logfile.write(query + "\n")
        with self.session.begin_transaction() as tx:
            result = tx.run(query)
        return result

    def create_method2class_rel(self, rel, m, c):
        query = 'MATCH (m:Method{name:"' + m + '"}),' \
                '(c:Class{name:"' + c + '"}) ' \
                'CREATE (m)-[:' + rel + ']->(c)'
        self.logfile.write(query + "\n")
        with self.session.begin_transaction() as tx:
            result = tx.run(query)
        return result

    def create_method2method_rel(self, rel, m1, m2):
        query = 'MATCH (m1:Method{name:"' + m1 + '"}),' \
                '(m2:Method{name:"' + m2 + '"}) ' \
                'CREATE (m1)-[:' + rel + ']->(m2)'
        self.logfile.write(query + "\n")
        with self.session.begin_transaction() as tx:
            result = tx.run(query)
        return result

    def cleanup(self):
        with self.session.begin_transaction() as tx:
            result = tx.run("MATCH (n) DETACH DELETE (n)")

parser = AntlrJavaParser()

files = sys.argv[1:]
for fn in files:
    parser.read_file(fn)
parser.parse_all()
r = parser.get_results(False)
print(str(r))

db = Neo4jDB()
db.open()

db.cleanup()
for c in r.keys():
    print(c)
    db.create_class_node_if_new(c)
    if r[c]["imports"]:
        for i in r[c]["imports"]:
            print("%s imports %s" % (c, i))
            db.create_class_node_if_new(i)
            db.create_class2class_rel("IMPORTS", c, i)
    if r[c]["extends"]:
        e = r[c]["extends"]
        print("%s extends %s" % (c, i))
        db.create_class_node_if_new(e)
        db.create_class2class_rel("EXTENDS", c, e)
    if r[c]["interfaces"]:
        for i in r[c]["interfaces"]:
            print("%s implements %s" % (c, i))
            db.create_class_node_if_new(i)
            db.create_class2class_rel("IMPLEMENTS", c, i)
    if r[c]["methods"]:
        for m in r[c]["methods"]:
            print("%s owns %s" % (c, m))
            db.create_method_node_if_new(m)
            db.create_class2method_rel("OWNS", c, m)
            for mv in r[c]["methods"][m]["vars"]:
                print("\t%s localvar %s" % (m, mv))
                db.create_class_node_if_new(mv)
                db.create_method2class_rel("USES_VAR", m, mv)
            for mv in r[c]["methods"][m]["args"]:
                print("\t%s args %s" % (m, mv))
                db.create_class_node_if_new(mv)
                db.create_method2class_rel("USES_ARG", m, mv)
            for mv in r[c]["methods"][m]["use"]:
                print("\t%s use %s" % (m, mv))
                db.create_class_node_if_new(mv)
                db.create_method2class_rel("USES", m, mv)
            for mv in r[c]["methods"][m]["calls"]:
                print("\t%s calls %s" % (m, mv))
                mv = mv.split(':')[-1]
                db.create_method_node_if_new(mv)
                db.create_method2method_rel("CALLS", m, mv)
            mv = r[c]["methods"][m]["return"]
            if mv:
                print("\t%s returns %s" % (m, mv))
                db.create_class_node_if_new(mv)
                db.create_method2class_rel("USES_RETURN", m, mv)
    if r[c]["composed"]:
        for cc in r[c]["composed"]:
            print("%s composed by %s" % (c, cc))
            db.create_class_node_if_new(cc)
            db.create_class2class_rel("COMPOSED_BY", c, cc)


