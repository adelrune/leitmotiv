import leitmotiv
interpreter = leitmotiv.LTVInterpreter()

def test_language():
    assert interpreter.evaluate_program("1") == leitmotiv.Reference(value=1)
