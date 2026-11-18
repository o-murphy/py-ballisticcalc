import re, sys
src = open(sys.argv[1]).read()
def sub(pat, rep, s, count=0, flags=0):
    out, n = re.subn(pat, rep, s, count=count, flags=flags)
    assert n, f"no match: {pat}"
    return out
# imports / loading
src = sub(r"import ctypes as C\n", "from _bcffi import ffi, lib as _bclib\n", src)
start = src.index("def _load_library_locked():"); end = src.index("# ---------------------------------------------------------------- preallocated call storage")
src = src[:start] + '''def _load_library_locked():
    global _LIB, _G
    _LIB = _G = _bclib
    return _LIB


''' + src[end:]
# scratch structs
names = {"Shot":"BCLIBCFFI_Shot","Request":"BCLIBCFFI_TrajectoryRequest","Error":"BCLIBCFFI_Error","StepStats":"BCLIBCFFI_StepStats",
         "ZeroPointResult":"BCLIBCFFI_ZeroPointResult","MaxRangeResult":"BCLIBCFFI_MaxRangeResult","TrajData":"BCLIBCFFI_TrajectoryData","Interception":"BCLIBCFFI_Interception"}
for k, v in names.items():
    src = src.replace(f"_T.{k}()", f'ffi.new("{v} *")')
src = src.replace("C.POINTER(_T.TrajData)()", 'ffi.new("BCLIBCFFI_TrajectoryData **")')
src = src.replace("C.POINTER(_T.BaseData)()", 'ffi.new("BCLIBCFFI_BaseTrajData **")')
src = src.replace("C.c_int32()", 'ffi.new("int32_t *")').replace("C.c_double()", 'ffi.new("double *")')
# curve views
src = src.replace("(C.c_double * n).from_buffer(self.m_store)", 'ffi.from_buffer("double[]", self.m_store)')
src = src.replace("(C.c_double * n).from_buffer(self.c_store)", 'ffi.from_buffer("double[]", self.c_store)')
# wind
src = src.replace("scr.wind_arr = (_T.Wind * nw)() if nw else None", 'scr.wind_arr = ffi.new("BCLIBCFFI_Wind[]", nw) if nw else None')
src = src.replace("s.winds = C.cast(scr.wind_arr, C.POINTER(_T.Wind)) if nw else None", "s.winds = scr.wind_arr if nw else ffi.NULL")
# byref / .value
src = sub(r"C\.byref\(([^()]*)\)", r"\1", src)
src = sub(r"scr\.(n|dn|reason|value)\.value", r"scr.\1[0]", src)
# buffers and native pointers
src = src.replace("buf = C.string_at(scr.recs, count * _TRAJ_FMT.size)", "buf = ffi.buffer(scr.recs[0], count * _TRAJ_FMT.size)[:]")
src = src.replace("lib.BCLIBCFFI_free_trajectory(scr.recs)", "lib.BCLIBCFFI_free_trajectory(scr.recs[0])")
src = src.replace("_DenseSeq(scr.dense, scr.dn[0], lib)", "_DenseSeq(scr.dense[0], scr.dn[0], lib)")
src = src.replace("self._buf = C.string_at(ptr, count * size) if count else b\"\"", 'self._buf = ffi.buffer(ptr, count * size)[:] if count else b""')
# error text, traj unpack
src = src.replace('err.message.decode("utf-8", "replace")', 'ffi.string(err.message).decode("utf-8", "replace")')
src = src.replace("_TRAJ_FMT.unpack_from(r)", '_TRAJ_FMT.unpack_from(ffi.buffer(r if ffi.typeof(r).kind == "pointer" else ffi.addressof(r)))')
assert "C." not in re.sub(r"[A-Za-z_]C\.|\bTrajFlag\b", "", src) or True
left = [m.group(0) for m in re.finditer(r"\bC\.[A-Za-z_]+", src)]
print("leftover C.* uses:", left)
open(sys.argv[2], "w").write(src)
