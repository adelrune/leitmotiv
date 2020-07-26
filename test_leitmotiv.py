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

def test_cond():
    assert ltv_eval(
        """
a = 4 + 3
if a == 6 {
    1
} else {
    0
}"""
    ) == mk_val(0)

def test_loop():
    assert ltv_eval(
        """
a = 0
while a < 5 {
    a = a + 1
}
"""
    ) == mk_val(5)

def test_list():
    assert ltv_eval(
        """
a = 0
b = [2,
    while a < 5 {
        a = a + 1
    },
    if 1 {
        4
    }
][1]
"""
    ) == mk_val(5)
