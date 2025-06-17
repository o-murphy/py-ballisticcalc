# Build
```shell
gcc -shared -o libv3d.so v3d.c -fPIC -lm
gcc -shared -o libbcb.so bindings.c v3d.c -fPIC -lm
```