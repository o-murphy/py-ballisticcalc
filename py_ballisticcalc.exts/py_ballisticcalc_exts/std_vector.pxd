# std::vector helpers without `except +`.
#
# libcpp.vector declares reserve()/resize()/emplace_back() with `except +`, which makes Cython emit try/catch
# around every call -- not compilable with -fno-exceptions. These inline C++ shims call them directly.
cdef extern from * nogil:
    """
    template <class V>
    static inline void vector_reserve(V &v, size_t n) noexcept { v.reserve(n); }

    template <class V>
    static inline void vector_resize(V &v, size_t n) noexcept { v.resize(n); }

    template <class V>
    static inline void vector_emplace_back4(V &v, double a, double b, double c, double d) noexcept {
        v.emplace_back(a, b, c, d);
    }
    """
    void vector_reserve[V](V &v, size_t n) noexcept
    void vector_resize[V](V &v, size_t n) noexcept
    void vector_emplace_back4[V](V &v, double a, double b, double c, double d) noexcept
