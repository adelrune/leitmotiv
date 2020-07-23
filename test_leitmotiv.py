import leitmotiv
interpreter = leitmotiv.LTVInterpreter()

def mk_val(value):
    return leitmotiv.Reference(value=value)

def ltv_eval(program):
    return interpreter.evaluate_program(program)

def test_operations():
    assert ltv_eval("1") == mk_val(1)
    assert ltv_eval("1 + 1 + 2 + 2 - 2") == mk_val(4)
