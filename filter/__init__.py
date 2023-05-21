from antlr4 import *
from parser.JavaParser import *
from parser.JavaParserListener import JavaParserListener
from parser.JavaParserVisitor import JavaParserVisitor


class FilteredListener(JavaParserListener):

    def __init__(self, classname="<No Name>"):
        super()
        self.classname = classname
        self.imports = set()
        self.extends = None
        self.interfaces = set()
        self.composed = set()
        self.methods = {}
        self._vars = set()

    def get_results(self):
        return {self.classname: {\
                    "imports": self.imports, \
                    "extends": self.extends, \
                    "interfaces": self.interfaces, \
                    "methods": self.methods, \
                    "composed": self.composed, \
                    "_var_map": self._vars, \
                    } \
                }

    # Helper
    def _init_method(self, method):
        self.methods[method] = {"vars":set(), "args":set(), "return":None, "use":set(), "calls":set(), "varinfo":set()}

    # Helper
    def _get_var_type(self, var, method=None):
        for v in self._vars:
            if not method: # No method specified : get both global and method's vars
                if v[0] == "global" and v[1] == var: # format: (global, name, class)
                    return v[2]
                elif v[0] == "local" and v[2] == var: # format: (local, method, name, class)
                    return v[3]
            else:
                if v[0] == "local" and v[1] == method and v[2] == var: # format: (local, method, name, class)
                    return v[3]

    def enterImportDeclaration(self, ctx:JavaParser.ImportDeclarationContext):
        # IMPORTS
        token = ctx.qualifiedName() # QualifiedNameContext
        self.imports.add(token.getText())

    def enterClassOrInterfaceType(self, ctx:JavaParser.ClassOrInterfaceTypeContext):
        """
        print("enterClassOrInterfaceType")
        c = ctx
        for i in range(3):
            print("\t"*(i+1) + str(type(c)))
            print("\t"*(i+1) + str(c.getText()))
            c = c.parentCtx
        """

        classname = ctx.getText() 
        c = ctx.parentCtx.parentCtx

        if isinstance(c, JavaParser.ClassDeclarationContext):
            # EXTENDS
            self.extends = classname

        elif isinstance(c, JavaParser.TypeListContext):
            # IMPLEMENTS
            self.interfaces.add(classname)

        elif isinstance(c, JavaParser.TypeArgumentContext):
            try:
                methodctx = c.parentCtx.parentCtx.parentCtx.parentCtx.parentCtx.parentCtx.parentCtx.parentCtx
                ident = methodctx.identifier()
                method = ident.getText()
            except:
                return
            if method not in self.methods.keys():
                self._init_method(method)
            # USES
            self.methods[method]["use"].add(classname)

        elif isinstance(c, JavaParser.FieldDeclarationContext):
            self.composed.add(classname)
            variables = c.variableDeclarators()
            for v in variables.variableDeclarator():
                ident = v.variableDeclaratorId().getText()
                #print("Variabile type:" + classname + " id: " + ident)
                self._vars.add( ("global", ident, classname) )

        elif isinstance(c, JavaParser.TypeTypeOrVoidContext):
            methodctx = c.parentCtx
            ident = methodctx.identifier()
            if ident is None:
                return
            method = ident.getText()
            if method not in self.methods.keys():
                self._init_method(method)
            # RETURNS
            #self.methods[method]["return"].add(classname)
            self.methods[method]["return"] = classname

        elif isinstance(c, JavaParser.FormalParameterContext):
            try:
                methodctx = c.parentCtx.parentCtx.parentCtx
                method = methodctx.identifier().getText()
            except:
                return
            if method not in self.methods.keys():
                self._init_method(method)
            # ARGS
            self.methods[method]["args"].add(classname)
        else:
            #print("TODO " + classname + str(type(ctx)) + " -> " + str(type(c)))
            pass
        
    def enterMethodCall(self, ctx:JavaParser.MethodCallContext):
        # ricava metodo e classe
        target_method = ctx.getText()
        # Strip parenthesis
        target_method = target_method[:target_method.find("(")]
        #print("Method call: " + ctx.getText())
        c = ctx;
        while not isinstance(c, JavaParser.MethodDeclarationContext):
            if c.parentCtx is None:
                return
            c = c.parentCtx
        #print(c.identifier().getText())
        source_method = c.identifier().getText()
        while not isinstance(c, JavaParser.ClassDeclarationContext):
            c = c.parentCtx
        source_class = c.identifier().getText();
        
        c = ctx.parentCtx # ExpressionContext
        try: # 
            target_var = c.expression()[0].getText()
            target_var_type = self._get_var_type(target_var)
        except:
            target_var_type = None
        if target_var_type == None:
            target_var_type = ".".join([x.getText() for x in c.expression()])
            if target_var_type == '':
                #target_var_type = self.classname
                # WARNING: call to a owned method
                return
        target_method = target_var_type + "::" + target_method
        #print("%s::%s -> %s" % (source_class, source_method, target_method))
        if source_method not in self.methods.keys():
            self._init_method(source_method)
        self.methods[source_method]["calls"].add(target_method)

    def enterLocalVariableDeclaration(self, ctx:JavaParser.LocalVariableDeclarationContext):
        try:
            # Recupero il metodo che contiene la/e variabile/i
            methodctx = ctx.parentCtx.parentCtx.parentCtx.parentCtx
            ident = methodctx.identifier()
            method = ident.getText()
        except:
            return
        # Prima volta?
        if method not in self.methods.keys():
                self._init_method(method)
        # Il tipo è una classe/interfaccia?
        isclass = ctx.typeType().classOrInterfaceType()
        if isclass:
            vtype = isclass.getText()
            self.methods[method]["vars"].add(vtype)
            variables = ctx.variableDeclarators()
            for v in variables.variableDeclarator():
                ident = v.variableDeclaratorId().getText()
                self.methods[method]["varinfo"].add( (ident, vtype) )
                #print("Variabile of <" + method + "> -  type:" + vtype + " id: " + ident)
                self._vars.add( ("local", method, ident, vtype) )
