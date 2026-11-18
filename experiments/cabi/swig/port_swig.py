import re, sys
src = open(sys.argv[1]).read()
def sub(pat, rep, s):
    out, n = re.subn(pat, rep, s); assert n, pat; return out
src = sub(r"import ctypes as C\n", "import bcswig as _bs\n", src)
a = src.index("def _load_library_locked():"); b = src.index("# ---------------------------------------------------------------- preallocated call storage")
src = src[:a] + "def _load_library_locked():\n    global _LIB, _G\n    _LIB = _G = _bs\n    return _LIB\n\n\n" + src[b:]
names = {"Shot":"BCLIBCFFI_Shot","Request":"BCLIBCFFI_TrajectoryRequest","Error":"BCLIBCFFI_Error","StepStats":"BCLIBCFFI_StepStats",
         "ZeroPointResult":"BCLIBCFFI_ZeroPointResult","MaxRangeResult":"BCLIBCFFI_MaxRangeResult","TrajData":"BCLIBCFFI_TrajectoryData","Interception":"BCLIBCFFI_Interception"}
for k, v in names.items():
    src = src.replace(f"_T.{k}()", f"_bs.{v}()")
src = src.replace("C.POINTER(_T.TrajData)()", "_bs.new_trajpp()").replace("C.POINTER(_T.BaseData)()", "_bs.new_basepp()")
src = src.replace("C.c_int32()", "_bs.new_int32p()").replace("C.c_double()", "_bs.new_doublep()")
src = src.replace("(C.c_double * n).from_buffer(self.m_store)", "_bs.bc_dptr(self.m_store.buffer_info()[0])")
src = src.replace("(C.c_double * n).from_buffer(self.c_store)", "_bs.bc_dptr(self.c_store.buffer_info()[0])")
src = src.replace("scr.wind_arr = (_T.Wind * nw)() if nw else None", "scr.wind_arr = _bs.WindArray(nw) if nw else None")
src = src.replace("s.winds = C.cast(scr.wind_arr, C.POINTER(_T.Wind)) if nw else None", "s.winds = scr.wind_arr.cast() if nw else None")
src = sub(r"C\.byref\(([^()]*)\)", r"\1", src)
src = sub(r"scr\.(n|dn|reason)\.value", r"_bs.int32p_value(scr.\1)", src)
src = sub(r"scr\.value\.value", r"_bs.doublep_value(scr.value)", src)
src = src.replace("buf = C.string_at(scr.recs, count * _TRAJ_FMT.size)", "buf = _bs.bc_bytes(_bs.trajpp_value(scr.recs), count * _TRAJ_FMT.size)")
src = src.replace("lib.BCLIBCFFI_free_trajectory(scr.recs)", "lib.BCLIBCFFI_free_trajectory(_bs.trajpp_value(scr.recs))")
src = src.replace("_DenseSeq(scr.dense, _bs.int32p_value(scr.dn), lib)", "_DenseSeq(_bs.basepp_value(scr.dense), _bs.int32p_value(scr.dn), lib)")
src = src.replace('self._buf = C.string_at(ptr, count * size) if count else b""', 'self._buf = _bs.bc_bytes(ptr, count * size) if count else b""')
src = src.replace('err.message.decode("utf-8", "replace")', "err.message")
src = src.replace("_TRAJ_FMT.unpack_from(r)", "_TRAJ_FMT.unpack_from(_bs.bc_bytes(r, _TRAJ_FMT.size))")
print("leftover:", [m.group(0) for m in re.finditer(r"\bC\.[A-Za-z_]+", src)])
open(sys.argv[2], "w").write(src)
