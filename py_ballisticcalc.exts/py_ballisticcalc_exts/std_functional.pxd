# std::function helpers that need no RTTI.
#
# std::function::target<T>() needs typeid, so it is unavailable with -fno-rtti. Instead of fishing the stored
# functor back out of a std::function, keep the functor in the owner (e.g. as a cdef-class attribute) and store a
# std::reference_wrapper to it, the way bclibc itself does (see bclibc/cash_karp.hpp).
cdef extern from * nogil:
    """
    #include <functional>

    template <class F, class T>
    static inline void function_assign_ref(F &f, T &target) noexcept { f = std::ref(target); }
    """
    void function_assign_ref[F, T](F &f, T &target) noexcept
