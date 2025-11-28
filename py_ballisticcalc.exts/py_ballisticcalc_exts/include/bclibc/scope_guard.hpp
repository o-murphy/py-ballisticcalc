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

    //     void dismiss() { active = false; }

    // private:
    //     std::function<void()> func;
    //     bool active;
    // };

    /**
     * @brief RAII guard for temporarily changing a variable's value.
     *
     * Saves the original value of a variable and restores it when the guard goes out of scope,
     * unless dismiss() is called.
     *
     * @tparam T Type of the variable to guard.
     *
     * @example
     * int x = 10;
     * {
     *     BCLIBC_ValueGuard<int> guard(&x, 20); // x = 20
     *     // work with x = 20
     * } // upon exiting scope, x is restored to 10
     */
    template <typename T>
    class BCLIBC_ValueGuard
    {
    public:
        /**
         * @brief Constructor.
         * @param target Pointer to the variable to temporarily modify.
         * @param new_value The new value to assign to the variable.
         */
        BCLIBC_ValueGuard(T *target, T new_value)
            : target(target), old_value(*target), active(true)
        {
            *target = new_value;
        }

        /**
         * @brief Destructor.
         *
         * Restores the old value if the guard is still active.
         */
        ~BCLIBC_ValueGuard()
        {
            if (active)
                *target = old_value;
        }

        /**
         * @brief Disable restoring the old value.
         *
         * After calling dismiss(), the original value will not be restored
         * when the guard goes out of scope.
         */
        void dismiss() { active = false; }

    private:
        T *target;   ///< Pointer to the guarded variable
        T old_value; ///< Original value to be restored
        bool active; ///< Flag indicating whether the guard is active
    };
}; // namespace bclibc

#endif // BCLIBC_SCOPE_GUARD_HPP
