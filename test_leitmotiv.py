import leitmotiv
interpreter = leitmotiv.LTVInterpreter()

def mk_val(value):
    return leitmotiv.Reference(value=value)

def ltv_eval(program):
    return interpreter.evaluate_program(program)

def test_operations():
    assert ltv_eval("1") == mk_val(1)
    assert ltv_eval("1 + -1 + 2 + 2 - 2") == mk_val(2)
    assert ltv_eval("2 + 8 * -4 + 2") == mk_val(-28)
    assert ltv_eval("2 + 8 * -4 % 7 // 2 + 2 / 3 - 4") == mk_val(-0.3333333333333335)
    assert ltv_eval("2 > 3") == mk_val(False)
    assert ltv_eval("3 == 4") == mk_val(False)
    assert ltv_eval("1 + 3 != 5") == mk_val(True)
    assert ltv_eval("5 * 4 >= 4") == mk_val(True)
    assert ltv_eval("1 <= 3+4 % 5") == mk_val(True)
    assert ltv_eval("7//2 < 7*8+3//5") == mk_val(True)
    assert ltv_eval("not 1") == mk_val(False)
    assert ltv_eval("not not not not not 1 - 1") == mk_val(True)
    assert ltv_eval("1 or 0") == mk_val(1)
    assert ltv_eval("1 and 0") == mk_val(0)
