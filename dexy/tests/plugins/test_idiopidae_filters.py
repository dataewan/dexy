from dexy.tests.utils import wrap
from dexy.doc import Doc

def test_multiple_sections():
    with wrap() as wrapper:
        src = """
### @export "vars"
x = 6
y = 7

### @export "multiply"
x*y

"""
        doc = Doc("example.py|idio",
                contents=src,
                wrapper=wrapper)

        wrapper.docs = [doc]
        wrapper.run()

        assert doc.output().keys() == ['1', 'vars', 'multiply']

def test_force_text():
    with wrap() as wrapper:
        doc = Doc("example.py|idio|t",
                contents="print 'hello'\n",
                wrapper=wrapper)
        wrapper.docs = [doc]
        wrapper.run()

        assert doc.output().as_text() == "print 'hello'\n"

def test_force_latex():
    with wrap() as wrapper:
        doc = Doc("example.py|idio|l",
                contents="print 'hello'\n",
                wrapper=wrapper)
        wrapper.docs = [doc]
        wrapper.run()

        assert "begin{Verbatim}" in doc.output().as_text()