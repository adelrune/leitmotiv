import sys
import lark
import ast
import random
from subprocess import run
import os
import shutil
import ltv_builtins

class Reference:
    def __init__(self, identifier=None, value=None):
        self.identifier = identifier
        self.value = value
    def __repr__(self):
        return f"({self.identifier} -> {self.value})"
    def __eq__(self, other):
        return self.identifier == other.identifier and self.value == other.value

class LTVFunc:
    def __init__(self, tokens, arguments, interpreter):
        self.tokens = tokens
        self.arg_list = [argument.identifier for argument in arguments]
        self.interpreter = interpreter
        contexts = list(filter(lambda x: x is ltv_builtins.global_scope, self.interpreter.context))
        self.closure_context = {ident: ctx[ident] for ctx in contexts for ident in ctx}

    def __call__(self, *args, **kwargs):
        argument_context = {self.arg_list[i]: arg for i, arg in enumerate(args)}
        self.interpreter.context.append({**argument_context, **self.closure_context})
        self.interpreter.context_level +=1
        last_value = None
        for tok in self.tokens:
            last_value = self.interpreter.get_terminal_value(tok)
        self.interpreter.context.pop()
        self.interpreter.context_level -=1
        return last_value.value

class LTVInterpreter:
    def __init__(self):
        self.program_lines = None
        self.context = None
        self.context_level = None
        self.grammar = open(__file__.split(".py")[0]+".lark", "r").read()
        self.parser = lark.Lark(self.grammar, propagate_positions=True)
        self.artifact_folder = "tmp_artifacts"

    def find_in_context(self, ident):
        ref = Reference(identifier=ident)
        current_ctx = self.context_level
        while current_ctx >= 0:
            if ident in self.context[current_ctx]:
                ref.value = self.context[current_ctx][ident]
                return ref
            current_ctx -=1
        return ref

    def get_terminal_value(self, tokens):

        if type(tokens) == lark.lexer.Token:
            if tokens.type == "CNAME":
                return self.find_in_context(tokens.value)

        if tokens.data == "getattr":
            source = self.get_terminal_value(tokens.children[0]).value
            attr = self.get_terminal_value(tokens.children[1]).identifier

            return Reference(value=source.scope[attr])

        elif tokens.data == "assignation":
            l_value = self.get_terminal_value(tokens.children[0])
            r_value = self.get_terminal_value(tokens.children[1])
            self.context[self.context_level][l_value.identifier] = r_value.value
            return r_value

        elif tokens.data == "display":

            pattern = self.get_terminal_value(tokens.children[0])
            img_name = pattern.value.generate_image()
            if self.program_lines is None:
                return None
            if len(tokens.children) > 1:
                self.program_lines[tokens.end_line-1] = self.program_lines[tokens.end_line-1].split(" ")[0] + f" {img_name}"
            else:
                self.program_lines[tokens.end_line-1] = self.program_lines[tokens.end_line-1] + f" {img_name}"
            return None

        elif tokens.data == "var":
            return self.find_in_context(tokens.children[0].value)

        elif tokens.data == "term" or tokens.data == "arith_expr" or tokens.data == "comparison":
            result = self.get_terminal_value(tokens.children[0]).value
            ops = {
                "+":lambda x, y: x+y,
                "-": lambda x, y: x-y,
                "*":lambda x,y: x*y,
                "/": lambda x,y: x/y,
                "//": lambda x,y: x//y,
                "/": lambda x,y: x/y,
                "%": lambda x,y: x%y,
                "<": lambda x,y: x<y,
                "<=": lambda x,y: x<=y,
                ">": lambda x,y: x>y,
                ">=": lambda x,y: x>=y,
                "==": lambda x,y: x==y,
                "!=": lambda x,y: x!=y
            }

            for i in range(1, len(tokens.children), 2):
                # because of parsing priority stuff, integer division has to be a rule and so is a Tree object
                op = tokens.children[i]
                if type(op) == lark.Tree:
                    op = op.children[0].value
                else:
                    op = op.value
                operand = self.get_terminal_value(tokens.children[i+1]).value
                result = ops[op](result, operand)
            return Reference(value = result)


        elif tokens.data == "abc_def":
            return Reference(value=ltv_builtins.Pattern(ast.literal_eval(tokens.children[0].value)))

        elif tokens.data == "arguments":
            return [self.get_terminal_value(child) for child in tokens.children]

        elif tokens.data == "fn_def":
            args = self.get_terminal_value(tokens.children[0])
            instructions = tokens.children[1].children[1:-1]
            return Reference(value=LTVFunc(instructions, args, self))

        elif tokens.data == "func_call":
            function = self.get_terminal_value(tokens.children[0]).value
            arguments = [arg.value for arg in self.get_terminal_value(tokens.children[1])]

            return Reference(value=function(*arguments))

        elif tokens.data == "side_effect_call":

            # get the source object
            source = self.get_terminal_value(tokens.children[0]).value
            # gets the identifier of the attr
            attr = self.get_terminal_value(tokens.children[2]).identifier
            # source->attr
            func = source.scope[attr]
            # calls the function with all its passed arguments and the side_effect=True flag
            print(func)
            return Reference(value=lambda *arg, **kwargs: func(side_effect=True, *arg, **kwargs))

        elif tokens.data == "number":
            if tokens.children[0].type == "DEC_NUMBER":
                return Reference(value=int(tokens.children[0].value))
            else:
                return Reference(value=float(tokens.children[0].value))

        elif tokens.data == "factor":
            return Reference(value=-self.get_terminal_value(tokens.children[1]).value)

        elif tokens.data == "string":
            return Reference(value=ast.literal_eval(tokens.children[0].value))



    def evaluate_file(self, fname):
        program = open(fname).read()
        self.artifact_folder = f"{fname}_artifacts"
        ltv_builtins.artifact_folder = self.artifact_folder
        self.program_lines = program.split("\n")
        self.evaluate_program(program)
        program = open(fname, "w").write("\n".join(self.program_lines))



    def evaluate_program(self, program):
        try:
            shutil.rmtree(self.artifact_folder)
        except:
            pass
        os.mkdir(self.artifact_folder)

        if program[-1] != "\n":
            program += "\n"
        self.parse_tree = self.parser.parse(program)
        self.context_level = 0
        self.context = [ltv_builtins.global_scope]
        last_value = None
        for instruction in self.parse_tree.children:
            last_value = self.get_terminal_value(instruction)
        return last_value



if __name__ == "__main__":
    interp = LTVInterpreter()
    interp.evaluate_file(sys.argv[1])
