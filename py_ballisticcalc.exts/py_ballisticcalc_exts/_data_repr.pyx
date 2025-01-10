cdef class _DataRepr:

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__

        # Collect attribute names, skipping magic methods (__something__)
        attr_names = [name for name in dir(self)
                      if not name.startswith("__")]

        # Filter out callables and properties
        attrs = {}
        for name in attr_names:
            value = getattr(self, name, None)
            if not callable(value) and not isinstance(getattr(self.__class__, name, None), property):
                attrs[name] = value

        # Format the output
        attr_str = ", ".join(f"{key}={repr(value)}" for key, value in attrs.items())
        return f"{cls_name}({attr_str})"
