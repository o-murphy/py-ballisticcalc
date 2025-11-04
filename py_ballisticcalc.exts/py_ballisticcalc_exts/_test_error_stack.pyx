# cython: freethreading_compatible=True
import inspect
from cpython.bytes cimport PyBytes_AsString
from libc.stdlib cimport malloc, free
from py_ballisticcalc_exts.error_stack cimport (
    BCLIBC_ErrorStack,
    BCLIBC_ErrorFrame,
    BCLIBC_ErrorStack_print,
    BCLIBC_ErrorStack_pushErr,
    BCLIBC_ErrorStack_clearErr,
    BCLIBC_ErrorStack_popErr,
    BCLIBC_ErrorStack_lastErr,
)

cdef class BCLIBC_ErrorStackT:
    cdef BCLIBC_ErrorStack* _c_stack_ptr
    cdef bint _own_memory

    def __cinit__(self):
        self._c_stack_ptr = <BCLIBC_ErrorStack*> malloc(sizeof(BCLIBC_ErrorStack))
        if not self._c_stack_ptr:
            raise MemoryError()
        self._c_stack_ptr.top = 0
        self._own_memory = True

    @staticmethod
    cdef BCLIBC_ErrorStackT from_c(BCLIBC_ErrorStack *c_stack):
        cdef BCLIBC_ErrorStackT stack = BCLIBC_ErrorStackT.__new__(BCLIBC_ErrorStackT)
        stack._c_stack_ptr = c_stack
        stack._own_memory = False
        return stack

    def __dealloc__(self):
        if self._own_memory and self._c_stack_ptr is not NULL:
            free(self._c_stack_ptr)

    @property
    def top(self):
        return self._c_stack_ptr.top

    @property
    def frames(self):
        return self._c_stack_ptr.frames

    def __getitem__(self, index):
        # handle slices first
        if isinstance(index, slice):
            # slice indices might be None; we can handle them with slice.indices()
            start, stop, step = index.indices(self._c_stack_ptr.top)
            return [
                _frame_as_dict(&self._c_stack_ptr.frames[i])
                for i in range(start, stop, step)
            ]

        # now handle integers
        if not isinstance(index, int):
            raise TypeError(f"Index must be int or slice, not {type(index).__name__}")

        if index < 0:
            index += self._c_stack_ptr.top  # support negative indices

        if index < 0 or index >= self._c_stack_ptr.top:
            raise IndexError("Index out of bound")

        return _frame_as_dict(&self._c_stack_ptr.frames[index])

    def push(self, code, src, msg):
        cdef bytes msg_bytes = msg.encode('utf-8')
        cdef frame = inspect.currentframe()
        cdef frameinfo = inspect.getframeinfo(frame.f_back)

        # cdef bytes func_bytes = frameinfo.function.encode('utf-8')
        # cdef bytes file_bytes = frameinfo.filename.encode('utf-8')
        cdef int line = frameinfo.lineno
        BCLIBC_ErrorStack_pushErr(
            self._c_stack_ptr,
            code,
            src,
            b'<cython>',
            b'<cython>',
            # PyBytes_AsString(func_bytes),
            # PyBytes_AsString(file_bytes),
            line,
            b"%s",
            PyBytes_AsString(msg_bytes)
        )

    def pop(self):
        BCLIBC_ErrorStack_popErr(self._c_stack_ptr)

    def clear(self):
        BCLIBC_ErrorStack_clearErr(self._c_stack_ptr)

    def last(self):
        cdef const BCLIBC_ErrorFrame *f = BCLIBC_ErrorStack_lastErr(self._c_stack_ptr)
        if f is NULL:
            return None
        # return f[0]
        return _frame_as_dict(f)

    def print_c_stack(self):
        BCLIBC_ErrorStack_print(self._c_stack_ptr)


# def raise_exception(self):
#     pass  # FIXME: redirect frames to python Exceptions


cdef object _frame_as_dict(BCLIBC_ErrorFrame *f):
    return {
        "code": f.code,
        "src": f.src,
        "func": f.func.decode('utf-8', 'ignore') if f.func is not NULL else "",
        "file": f.file.decode('utf-8', 'ignore') if f.file is not NULL else "",
        "line": f.line,
        "msg": f.msg.decode('utf-8', 'ignore') if f.msg is not NULL else ""
    }
