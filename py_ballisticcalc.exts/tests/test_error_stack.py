from py_ballisticcalc_exts.error_stack import ErrorStackT


def test_error_stack():
    test_msg = "test"
    stack = ErrorStackT()
    stack.push(0, 0, test_msg)
    print(stack)


    assert stack.top == 1
    first = stack.last()
    assert first
    assert first['code'] == 0
    assert first['msg'] == test_msg
    assert stack[0] == first

    stack.push(1, 1, "<cython>")
    assert stack.top == 2
    second = stack.last()
    assert second['code'] == 1
    assert stack[0] == first
    assert stack[1] == second

    stack.pop()
    assert stack.top == 1
    assert stack.last() == first

    assert stack[0] == first