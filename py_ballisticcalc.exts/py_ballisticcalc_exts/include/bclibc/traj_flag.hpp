#ifndef BCLIBC_TRAJ_FLAGS_HPP
#define BCLIBC_TRAJ_FLAGS_HPP

#include <type_traits>

namespace bclibc
{
    enum class BCLIBC_TrajFlag : unsigned int
    {
        NONE = 0,
        ZERO_UP = 1,
        ZERO_DOWN = 2,
        ZERO = ZERO_UP | ZERO_DOWN,
        MACH = 4,
        RANGE = 8,
        APEX = 16,
        ALL = RANGE | ZERO_UP | ZERO_DOWN | MACH | APEX,
        MRT = 32
    };

    // Helper function to check if any bits are set (for use in if statements)
    constexpr bool to_bool(BCLIBC_TrajFlag flag) noexcept
    {
        return static_cast<std::underlying_type<BCLIBC_TrajFlag>::type>(flag) != 0;
    }

    // Explicit conversion to bool
    constexpr bool operator!(BCLIBC_TrajFlag flag) noexcept
    {
        return static_cast<std::underlying_type<BCLIBC_TrajFlag>::type>(flag) == 0;
    }

    // Bitwise OR
    inline BCLIBC_TrajFlag operator|(BCLIBC_TrajFlag lhs, BCLIBC_TrajFlag rhs)
    {
        using T = std::underlying_type<BCLIBC_TrajFlag>::type;
        return static_cast<BCLIBC_TrajFlag>(static_cast<T>(lhs) | static_cast<T>(rhs));
    }

    // Bitwise AND
    inline BCLIBC_TrajFlag operator&(BCLIBC_TrajFlag lhs, BCLIBC_TrajFlag rhs)
    {
        using T = std::underlying_type<BCLIBC_TrajFlag>::type;
        return static_cast<BCLIBC_TrajFlag>(static_cast<T>(lhs) & static_cast<T>(rhs));
    }

    // Bitwise XOR
    inline BCLIBC_TrajFlag operator^(BCLIBC_TrajFlag lhs, BCLIBC_TrajFlag rhs)
    {
        using T = std::underlying_type<BCLIBC_TrajFlag>::type;
        return static_cast<BCLIBC_TrajFlag>(static_cast<T>(lhs) ^ static_cast<T>(rhs));
    }

    // Bitwise NOT
    inline BCLIBC_TrajFlag operator~(BCLIBC_TrajFlag rhs)
    {
        using T = std::underlying_type<BCLIBC_TrajFlag>::type;
        return static_cast<BCLIBC_TrajFlag>(~static_cast<T>(rhs));
    }

    // Compound assignment |=
    inline BCLIBC_TrajFlag &operator|=(BCLIBC_TrajFlag &lhs, BCLIBC_TrajFlag rhs)
    {
        lhs = lhs | rhs;
        return lhs;
    }

    // Compound assignment &=
    inline BCLIBC_TrajFlag &operator&=(BCLIBC_TrajFlag &lhs, BCLIBC_TrajFlag rhs)
    {
        lhs = lhs & rhs;
        return lhs;
    }

    // Compound assignment ^=
    inline BCLIBC_TrajFlag &operator^=(BCLIBC_TrajFlag &lhs, BCLIBC_TrajFlag rhs)
    {
        lhs = lhs ^ rhs;
        return lhs;
    }

    // & to bool halper
    inline bool hasFlag(BCLIBC_TrajFlag value, BCLIBC_TrajFlag flag)
    {
        return (value & flag) == flag;
    }
}

#endif // BCLIBC_TRAJ_FLAGS_HPP