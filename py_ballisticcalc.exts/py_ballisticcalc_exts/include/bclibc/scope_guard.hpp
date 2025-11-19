#ifndef BCLIBC_SCOPE_GUARD_HPP
#define BCLIBC_SCOPE_GUARD_HPP

// #include <functional> // for std::function
#include <utility>

namespace bclibc
{
    // class BCLIBC_ScopeGuard
    // {
    // public:
    //     template <typename F>
    //     BCLIBC_ScopeGuard(F &&f) : func(std::forward<F>(f)), active(true) {}

    //     ~BCLIBC_ScopeGuard()
    //     {
    //         if (active)
    //             func();
    //     }

    //     // можна вимкнути відновлення вручну
    //     void dismiss() { active = false; }

    // private:
    //     std::function<void()> func;
    //     bool active;
    // };

    template <typename T>
    class BCLIBC_ValueGuard
    {
    public:
        BCLIBC_ValueGuard(T *target, T new_value)
            : target(target), old_value(*target), active(true)
        {
            *target = new_value;
        }

        ~BCLIBC_ValueGuard()
        {
            if (active)
                *target = old_value;
        }

        void dismiss() { active = false; }

    private:
        T *target;
        T old_value;
        bool active;
    };
};

#endif // BCLIBC_SCOPE_GUARD_HPP
